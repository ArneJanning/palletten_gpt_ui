FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir streamlit>=1.28.0 requests>=2.31.0 python-dotenv>=1.0.0 PyPDF2>=3.0.0

# Copy application code and env files
COPY app.py ./
COPY .env* ./

# Expose Streamlit port
EXPOSE 8504

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8504/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8504", "--server.address=0.0.0.0", "--server.headless=true", "--server.fileWatcherType=none", "--browser.gatherUsageStats=false"]