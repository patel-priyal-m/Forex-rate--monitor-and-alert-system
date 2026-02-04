# Use official Python runtime as base image
FROM python:3.11-slim

# Set maintainer label
LABEL maintainer="priyalpatelasd@gmail.com"
LABEL description="FX Rate Producer - Fetches exchange rates and publishes to Kafka"

# Set working directory inside container
WORKDIR /app

# Install system dependencies required for confluent-kafka (librdkafka)
# gcc: C compiler for building Python C extensions
# g++: C++ compiler (librdkafka dependency)
# librdkafka-dev: Kafka C client library headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (Docker layer caching optimization)
# If requirements.txt doesn't change, this layer is cached
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Don't store pip cache (reduces image size)
# --upgrade: Ensure latest versions of pip/setuptools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy producer package files
COPY producer/ ./producer/

# Copy common utilities (for Phase 3)
COPY common/ ./common/

# Set Python path so imports work correctly
ENV PYTHONPATH=/app

# Create non-root user for security
# Running as root in containers is a security risk
RUN useradd -m -u 1000 fxuser && \
    chown -R fxuser:fxuser /app

# Switch to non-root user
USER fxuser

# Health check: verify Python and confluent_kafka are installed
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from confluent_kafka import Producer; print('OK')" || exit 1

# Run the producer script
CMD ["python", "-u", "producer/fx_producer.py"]
