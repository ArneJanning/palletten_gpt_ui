# Paletten-Gigant GraphRAG Chat Interface

A Streamlit-based chat interface for querying documents using GraphRAG, specifically designed for Paletten-Gigant.

## Features

- ChatGPT-like conversation interface (in German)
- Multiple search modes (local, global, drift)
- Configurable search parameters
- Response metadata and performance metrics
- **📖 Clickable PDF citations** - View source documents directly in the chat
- **🔍 Automatic citation detection** - Detects PDF references in responses
- **📁 Document viewer** - Built-in PDF viewer for source documents
- Docker support for easy deployment

## Quick Start

### Development (with external backend)

If you have a GraphRAG backend running locally on `http://127.0.0.1:9000`:

```bash
# Copy and configure environment file
cp .env.example .env
# Edit .env to set your API endpoint

# Place your PDF documents in the documents folder
mkdir -p documents
# Copy your PDF files to ./documents/

# Run with Docker
docker-compose -f docker-compose.dev.yml up --build

# Or run locally
pip install streamlit requests python-dotenv PyPDF2
streamlit run app.py
```

### Full Stack (with Docker)

```bash
# Start both frontend and backend
docker-compose up --build
```

### Production (with nginx-proxy and LetsEncrypt)

```bash
# Start production deployment
docker-compose -f docker-compose.prod.yml --env-file .env.prod up --build -d
```

**Requirements:**
- Running nginx-proxy container
- Running acme-companion container  
- Domain pointing to server IP

**Note**: You'll need to replace the `graphrag-backend` service in `docker-compose.yml` with your actual GraphRAG backend configuration.

## Configuration

### Environment Variables (.env file)

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Available settings:

- `API_BASE_URL`: Backend API URL (default: `http://127.0.0.1:9000`)
- `API_TIMEOUT`: API request timeout in seconds (default: `30`)
- `API_MAX_RETRIES`: Maximum retry attempts (default: `3`)
- `APP_TITLE`: Application title (default: `GraphRAG Chat Interface for Paletten-Gigant`)
- `DEFAULT_SEARCH_MODE`: Default search mode - local/global/drift (default: `local`)
- `DEFAULT_K_VALUE`: Default number of results for local search (default: `20`)
- `DEFAULT_INCLUDE_CONTEXT`: Include context data by default - true/false (default: `false`)
- `DEFAULT_INCLUDE_CITATIONS`: Include citations by default - true/false (default: `true`)
- `DOCUMENTS_PATH`: Path to PDF documents directory (default: `./documents`)
- `ENABLE_PDF_VIEWER`: Enable PDF viewer functionality - true/false (default: `true`)

### Search Parameters

- **Search Mode**: 
  - `local`: For specific information
  - `global`: For summaries
  - `drift`: Combined approach
- **k**: Number of results for local search (1-100)
- **Include Context**: Include raw context data in response
- **Include Citations**: Include enhanced citations

## API Endpoints Used

- `POST /query`: Main query endpoint
- `GET /health`: Health check endpoint

## Docker Commands

```bash
# Development (connect to external backend)
docker-compose -f docker-compose.dev.yml up --build

# Full stack
docker-compose up --build

# Build only the UI
docker build -t palletten-ui .

# Run UI container only
docker run -p 8503:8501 -e API_BASE_URL=http://host.docker.internal:9000 palletten-ui
```

## Access

### Development
- **Streamlit UI**: http://localhost:8503
- **Backend API**: http://localhost:9000 (if using full stack)
- **API Documentation**: http://localhost:9000/docs

### Production
- **Public URL**: https://palettenweb.paperworx.ai
- **SSL**: Automatic LetsEncrypt certificate
- **Email**: janning@aispezialisten.ai

## PDF Document Viewer

The application automatically detects PDF file references in GraphRAG responses and makes them clickable.

### Setup:

1. **Place PDF files** in the `./documents/` directory
2. **Configure path** in `.env` file: `DOCUMENTS_PATH=./documents`
3. **Enable viewer** in `.env` file: `ENABLE_PDF_VIEWER=true`

### Features:

- **Automatic detection**: Recognizes various citation formats (e.g., `[filename.pdf]`, `Source: filename.pdf`)
- **Clickable buttons**: Each detected PDF appears as a clickable button below the response
- **Built-in viewer**: PDFs open directly in the chat interface
- **Easy navigation**: Close PDF viewer from sidebar or continue chatting

### Supported citation formats:

- `[document.pdf]`
- `Source: document.pdf`
- `Quelle: document.pdf`
- `aus document.pdf`
- `from document.pdf`
- Direct mentions: `document.pdf`