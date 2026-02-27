# Multi-stage build for Rust Core Engine
FROM rust:1.89-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libpq-dev \
    protobuf-compiler \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source code
COPY . .
COPY ../../../microservices/proto ./proto

# Generate gRPC code
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    libpq5 \
    ca-certificates \
    libsasl2-3 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -r -s /bin/false coreengine

WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/target/release/core-engine /usr/local/bin/core-engine

# Copy configuration files
COPY --from=builder /app/config ./config

# Set permissions
RUN chown -R coreengine:coreengine /app
RUN chmod +x /usr/local/bin/core-engine

# Switch to non-root user
USER coreengine

# Expose gRPC port
EXPOSE 50052

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["/bin/sh", "-c", "grpc_health_probe -addr=:50052 || exit 1"]

# Set environment variables
ENV RUST_LOG=info
ENV NUM_PROCESSORS=4
ENV BUFFER_SIZE=1048576

# Run application
CMD ["core-engine"]
