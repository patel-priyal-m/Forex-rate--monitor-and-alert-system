# Use official Python runtime as base image
FROM python:3.11-slim

# Set maintainer label
LABEL maintainer="priyalpatelasd@gmail.com"
LABEL description="FX Rate Monitor API - FastAPI REST API"

# Set working directory inside container
WORKDIR /app

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (Docker layer caching optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy API package files
COPY api/ ./api/

# Copy common utilities (shared between services)
COPY common/ ./common/

# Set Python path so imports work correctly
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Create non-root user for security
RUN useradd -m -u 1000 fxuser && \
    chown -R fxuser:fxuser /app

# Switch to non-root user
USER fxuser

# Health check: verify API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run the API server
CMD ["python", "-u", "api/main.py"]
