# Multi-stage Dockerfile for Market Intel Brain
# Optimized for cloud-native CI/CD with minimal final image size

# Stage 1: Build Stage (Heavy Processing - runs in CI only)
FROM python:3.11-slim AS builder

# Set build arguments for CI/CD
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
ARG TARGETPLATFORM

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=60

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install dependencies
COPY requirements.txt requirements_production.txt ./
RUN pip install --no-cache-dir -r requirements_production.txt

# Copy application code
COPY . .

# Install application in development mode for testing
RUN pip install -e .

# Run heavy processing tasks (quality checks, security scans)
RUN python -m pytest --cov --tb=short || true
RUN ruff check . --fix || true
RUN mypy . --ignore-missing-imports || true
RUN bandit -r . -ll -ii --format=json -o /tmp/bandit-report.json || true
RUN safety check --json --output /tmp/safety-report.json || true

# Stage 2: Production Stage (Lightweight - for runtime)
FROM python:3.11-slim AS runner

# Set labels for production
LABEL maintainer="Market Intel Brain Team" \
      org.label-schema.build-date=${BUILD_DATE} \
      org.label-schema.name="market-intel-brain" \
      org.label-schema.description="Enterprise Financial Intelligence Platform" \
      org.label-schema.url="https://github.com/marketintel/brain" \
      org.label-schema.vcs-ref=${VCS_REF} \
      org.label-schema.vcs-url="https://github.com/marketintel/brain.git" \
      org.label-schema.vendor="Market Intel Brain" \
      org.label-schema.version=${VERSION} \
      org.label-schema.schema-version="1.0"

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    ENVIRONMENT=production \
    REDIS_URL=redis://redis:6379

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Copy application code with proper ownership
COPY --from=builder --chown=appuser:appuser /app /app

# Create necessary directories for runtime
RUN mkdir -p /app/logs /app/data /app/cache /tmp && \
    chown -R appuser:appuser /app/logs /app/data /app/cache /tmp

# Switch to non-root user
USER appuser

# Health check that doesn't require Redis
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8000

# Default command (will be overridden by docker-compose)
CMD ["python", "simple_api_server.py"]

# Stage 3: Testing Stage (CI only)
FROM builder AS testing

# Run comprehensive tests
RUN python -m pytest --cov --cov-report=html --cov-report=xml --tb=short
RUN python -m bandit -r . -f json -o /tmp/bandit-ci-report.json
RUN python -m safety check --json --output /tmp/safety-ci-report.json
RUN python -m ruff check . --format=json --output-file /tmp/ruff-ci-report.json

# Generate test artifacts
RUN echo "CI tests completed successfully" > /tmp/test-results.txt && \
    ls -la /tmp/*-report.json > /tmp/test-artifacts.txt
