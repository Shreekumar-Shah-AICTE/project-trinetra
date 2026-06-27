# ============================================================================
# Project Trinetra (त्रिनेत्र) — Docker Sandbox & Production Container
# ============================================================================
# Supports:
#   1. Streamlit Dashboard (Recruiter & Judges Panel)
#   2. CLI Pipeline Runner (Stage 3 Sandboxed Reproduction)
# ============================================================================

FROM python:3.11-slim

# System setup
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and evaluation directories
COPY src/ ./src/
COPY eval/ ./eval/
COPY data/ ./data/
COPY tests/ ./tests/

# Copy configuration and root files
COPY ARCHITECTURE.md DESIGN.md README.md ./

# Create output directories for CLI runs
RUN mkdir -p outputs

# Expose Streamlit port
EXPOSE 8501

# Default environment variables
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Healthcheck to verify Streamlit container health
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Default command starts the Streamlit interactive dashboard
CMD ["streamlit", "run", "src/app.py"]
