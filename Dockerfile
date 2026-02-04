# Production-ready multi-stage Dockerfile for FastAPI Todo Backend
# Base image: Python 3.11 slim for minimal footprint and security
# Target image size: < 500MB

# ============================================================================
# Stage 1: Builder - Install dependencies and build artifacts
# ============================================================================
FROM python:3.11.11-slim AS builder

# Set environment variables for build optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies required for compiling Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        postgresql-client \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment for isolated dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file for dependency installation
COPY requirements.txt .

# Install Python dependencies in virtual environment
# Pin versions are already specified in requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Production - Minimal runtime image
# ============================================================================
FROM python:3.11.11-slim AS production

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime dependencies (no build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1001 -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser . .

# Create directories for alembic migrations and logs with proper permissions
RUN mkdir -p /app/alembic/versions && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 8000 (FastAPI default)
EXPOSE 8000

# Health check configuration
# Checks /health endpoint every 30s with 3s timeout
# Starts checking after 10s, allows 3 retries before marking unhealthy
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
# Uses uvicorn ASGI server with production settings:
# - Host 0.0.0.0 to accept connections from outside container
# - Port 8000 (standard HTTP)
# - No reload in production for performance
# - Workers can be configured via environment variable (default 1)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
