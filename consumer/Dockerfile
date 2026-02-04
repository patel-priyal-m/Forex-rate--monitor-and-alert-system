# Use official Python runtime as base image
FROM python:3.11-slim

# Set maintainer label
LABEL maintainer="priyalpatelasd@gmail.com"
LABEL description="FX Rate Consumer - Processes messages from Kafka"

# Set working directory inside container
WORKDIR /app

# Install system dependencies required for confluent-kafka and psycopg2
# gcc: C compiler for building Python C extensions
# g++: C++ compiler (librdkafka dependency)
# librdkafka-dev: Kafka C client library headers
# libpq-dev: PostgreSQL client library headers (for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    librdkafka-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (Docker layer caching optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy consumer package files
COPY consumer/ ./consumer/

# Copy __init__.py to maintain package structure
COPY consumer/__init__.py ./consumer/

# Set Python path so imports work correctly
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd -m -u 1000 fxuser && \
    chown -R fxuser:fxuser /app

# Switch to non-root user
USER fxuser

# Health check: verify Python and confluent_kafka are installed
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from confluent_kafka import Consumer; print('OK')" || exit 1

# Run the consumer script
CMD ["python", "-u", "consumer/rate_processor.py"]
