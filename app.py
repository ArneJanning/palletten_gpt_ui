import streamlit as st
import requests
import json
import os
import re
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:9000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
APP_TITLE = os.getenv("APP_TITLE", "GraphRAG Chat Interface for Paletten-Gigant")
DEFAULT_SEARCH_MODE = os.getenv("DEFAULT_SEARCH_MODE", "local")
DEFAULT_K_VALUE = int(os.getenv("DEFAULT_K_VALUE", "20"))
DEFAULT_INCLUDE_CONTEXT = os.getenv("DEFAULT_INCLUDE_CONTEXT", "false").lower() == "true"
DEFAULT_INCLUDE_CITATIONS = os.getenv("DEFAULT_INCLUDE_CITATIONS", "true").lower() == "true"
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")
ENABLE_PDF_VIEWER = os.getenv("ENABLE_PDF_VIEWER", "true").lower() == "true"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💬",
    layout="wide"
)

def extract_citations_from_text(text: str) -> List[str]:
    """Extract file citations from response text."""
    # Common patterns for citations in GraphRAG responses
    patterns = [
        r'\[([^[\]]+\.pdf)\]',  # [filename.pdf] - exact brackets
        r'Source:\s*([^,\n]+\.pdf)',  # Source: filename.pdf
        r'Quelle:\s*([^,\n]+\.pdf)',  # Quelle: filename.pdf (German)
        r'aus\s+(?:dem\s+Dokument\s+)?([^,\s]+\.pdf)',  # aus (dem Dokument) filename.pdf
        r'from\s+([^,\s]+\.pdf)',  # from filename.pdf
        r'([A-Za-z0-9_€().-]+\.pdf)\.txt',  # .pdf.txt files (converted) - this should come first
        r'(?:^|\s)([A-Za-z0-9_€().-]+\.pdf)(?:\s|$|[,.])',  # Direct PDF filename with word boundaries
    ]
    
    citations = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Clean up the match
            clean_match = match.strip()
            # Remove trailing punctuation
            clean_match = re.sub(r'[.,;!?]+$', '', clean_match)
            if clean_match:
                citations.add(clean_match)
    
    # Also check for any .pdf.txt pattern anywhere in text
    pdf_txt_pattern = r'([A-Za-z0-9_€().\s-]+\.pdf)\.txt'
    pdf_txt_matches = re.findall(pdf_txt_pattern, text, re.IGNORECASE)
    for match in pdf_txt_matches:
        clean_match = match.strip()
        if clean_match:
            citations.add(clean_match)
    
    # Clean citations list
    cleaned_citations = set()
    for citation in citations:
        # Remove .txt extension if it exists after .pdf
        if citation.endswith('.pdf.txt'):
            citation = citation[:-4]  # Remove .txt
        cleaned_citations.add(citation)
    
    return list(cleaned_citations)

def find_pdf_file(filename: str) -> Optional[Path]:
    """Find PDF file in documents directory."""
    if not ENABLE_PDF_VIEWER:
        return None
        
    # Check if we're in a container environment
    if os.path.exists("/app/documents"):
        docs_path = Path("/app/documents")
    else:
        docs_path = Path(DOCUMENTS_PATH)
        
    if not docs_path.exists():
        return None
    
    # Clean filename for better matching
    clean_filename = filename.strip()
    
    # Try exact match first
    exact_match = docs_path / clean_filename
    if exact_match.exists() and exact_match.suffix.lower() == '.pdf':
        return exact_match
    
    # Try case-insensitive search
    for pdf_file in docs_path.rglob("*.pdf"):
        if pdf_file.name.lower() == clean_filename.lower():
            return pdf_file
    
    # Try partial match with base filename (without path)
    base_filename = Path(clean_filename).name.lower()
    for pdf_file in docs_path.rglob("*.pdf"):
        if base_filename in pdf_file.name.lower():
            return pdf_file
    
    # Try fuzzy matching - look for key parts of filename
    if len(base_filename) > 10:  # Only for longer filenames
        # Extract key parts (remove common extensions and timestamps)
        key_parts = re.sub(r'__eingefügt_am_.*', '', base_filename)
        key_parts = re.sub(r'\.pdf.*', '', key_parts)
        
        for pdf_file in docs_path.rglob("*.pdf"):
            pdf_base = pdf_file.name.lower()
            if key_parts in pdf_base or any(part in pdf_base for part in key_parts.split('_') if len(part) > 3):
                return pdf_file
    
    return None

def display_pdf_viewer(pdf_path: Path):
    """Display PDF in Streamlit."""
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        # PDF viewer using HTML iframe
        pdf_display = f'''
        <iframe src="data:application/pdf;base64,{base64_pdf}" 
                width="100%" height="600" type="application/pdf">
        </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Fehler beim Laden der PDF: {str(e)}")

def create_citation_links(text: str) -> str:
    """Create clickable links for citations in text."""
    if not ENABLE_PDF_VIEWER:
        return text
    
    citations = extract_citations_from_text(text)
    
    for citation in citations:
        pdf_path = find_pdf_file(citation)
        if pdf_path:
            # Create a unique key for this citation
            citation_key = f"pdf_{citation.replace('.', '_').replace(' ', '_')}"
            # Replace citation with clickable link
            link_html = f'<span style="color: #1f77b4; cursor: pointer; text-decoration: underline;" onclick="window.parent.postMessage({{type: \'show_pdf\', filename: \'{citation}\'}}, \'*\')">{citation}</span>'
            text = text.replace(citation, link_html)
    
    return text

def query_backend(query: str, mode: str = "local", k: int = 20, include_context: bool = False, include_citations: bool = True) -> Optional[Dict[str, Any]]:
    """Send query to the backend API."""
    try:
        payload = {
            "query": query,
            "mode": mode,
            "k": k,
            "include_context": include_context,
            "include_citations": include_citations
        }
        
        response = requests.post(
            f"{API_BASE_URL}/query",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

def main():
    st.title(f"💬 {APP_TITLE}")
    st.markdown("Stellen Sie Fragen zu Ihren Dokumenten mit GraphRAG-Suche.")
    
    # Initialize session state for PDF viewer
    if "show_pdf" not in st.session_state:
        st.session_state.show_pdf = None
    if "pdf_viewer_open" not in st.session_state:
        st.session_state.pdf_viewer_open = False
    
    # Show current API endpoint in sidebar
    with st.sidebar:
        st.header("⚙️ Einstellungen")
        st.info(f"🔗 API: {API_BASE_URL}")
        
        if ENABLE_PDF_VIEWER:
            st.info(f"📁 Dokumente: {DOCUMENTS_PATH}")
            
            # PDF viewer controls
            if st.session_state.pdf_viewer_open and st.session_state.show_pdf:
                if st.button("📖 PDF schließen"):
                    st.session_state.pdf_viewer_open = False
                    st.session_state.show_pdf = None
                    st.rerun()
        
        # Get default mode index
        mode_options = ["local", "global", "drift"]
        default_mode_index = mode_options.index(DEFAULT_SEARCH_MODE) if DEFAULT_SEARCH_MODE in mode_options else 0
        
        search_mode = st.selectbox(
            "Suchmodus",
            options=mode_options,
            index=default_mode_index,
            help="Local: spezifische Informationen, Global: Zusammenfassungen, Drift: kombinierter Ansatz"
        )
        
        if search_mode == "local":
            k_value = st.slider("Anzahl Ergebnisse (k)", min_value=1, max_value=100, value=DEFAULT_K_VALUE)
        else:
            k_value = DEFAULT_K_VALUE
            
        include_context = st.checkbox("Kontext-Daten einschließen", value=DEFAULT_INCLUDE_CONTEXT)
        include_citations = st.checkbox("Zitate einschließen", value=DEFAULT_INCLUDE_CITATIONS)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # PDF Viewer Section
    if st.session_state.pdf_viewer_open and st.session_state.show_pdf:
        st.header(f"📖 {st.session_state.show_pdf}")
        pdf_path = find_pdf_file(st.session_state.show_pdf)
        if pdf_path:
            display_pdf_viewer(pdf_path)
        else:
            st.error(f"PDF nicht gefunden: {st.session_state.show_pdf}")
        st.divider()
    
    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and ENABLE_PDF_VIEWER:
                # Extract citations and create buttons for them
                citations = extract_citations_from_text(message["content"])
                
                # Display response text
                st.markdown(message["content"])
                
                # Debug information (remove later)
                if st.checkbox(f"Debug Info {i}", key=f"debug_{i}"):
                    st.write(f"Citations found: {citations}")
                    st.write(f"Documents path: {'/app/documents' if os.path.exists('/app/documents') else DOCUMENTS_PATH}")
                    if os.path.exists("/app/documents"):
                        pdfs = list(Path("/app/documents").glob("*.pdf"))
                        st.write(f"Available PDFs: {[p.name for p in pdfs[:5]]}")
                
                # Display citation buttons
                if citations:
                    st.markdown("**📄 Quellen:**")
                    cols = st.columns(min(len(citations), 4))
                    for idx, citation in enumerate(citations):
                        with cols[idx % 4]:
                            if st.button(f"📖 {citation}", key=f"cite_{i}_{idx}"):
                                st.session_state.show_pdf = citation
                                st.session_state.pdf_viewer_open = True
                                st.rerun()
                else:
                    # Show debug for no citations found
                    if len(message["content"]) > 0:
                        st.info("Keine PDF-Zitate in dieser Antwort erkannt.")
            else:
                st.markdown(message["content"])
            
            # Show metadata for assistant responses
            if message["role"] == "assistant" and "metadata" in message:
                with st.expander("📊 Antwort-Details"):
                    metadata = message["metadata"]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Bearbeitungszeit", f"{metadata.get('completion_time', 0):.2f}s")
                    with col2:
                        st.metric("LLM-Aufrufe", metadata.get('llm_calls', 0))
                    with col3:
                        st.metric("Prompt-Token", metadata.get('prompt_tokens', 0))
                    
                    if metadata.get('context_data') and include_context:
                        st.json(metadata['context_data'])
    
    # Chat input
    if prompt := st.chat_input("Stellen Sie eine Frage zu Ihren Dokumenten..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                response_data = query_backend(
                    query=prompt,
                    mode=search_mode,
                    k=k_value,
                    include_context=include_context,
                    include_citations=include_citations
                )
            
            if response_data and not response_data.get('error'):
                # Display the response
                response_text = response_data.get('response', 'No response received')
                st.markdown(response_text)
                
                # Add assistant message to chat history with metadata
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response_text,
                    "metadata": response_data
                })
                
                # Show response details
                with st.expander("📊 Response Details"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Completion Time", f"{response_data.get('completion_time', 0):.2f}s")
                    with col2:
                        st.metric("LLM Calls", response_data.get('llm_calls', 0))
                    with col3:
                        st.metric("Prompt Tokens", response_data.get('prompt_tokens', 0))
                    
                    if response_data.get('context_data') and include_context:
                        st.json(response_data['context_data'])
                        
            elif response_data and response_data.get('error'):
                error_msg = f"❌ Error: {response_data['error']}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                error_msg = "❌ Failed to get response from the backend."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Clear chat button
    if st.sidebar.button("🗑️ Chat-Verlauf löschen"):
        st.session_state.messages = []
        st.session_state.pdf_viewer_open = False
        st.session_state.show_pdf = None
        st.rerun()

if __name__ == "__main__":
    main()