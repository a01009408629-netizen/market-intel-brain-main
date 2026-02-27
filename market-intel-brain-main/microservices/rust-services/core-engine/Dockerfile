# Multi-stage build for Rust Core Engine
FROM rust:1.88-slim-bookworm as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsasl2-dev \
    pkg-config \
    libssl-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Cargo files
COPY Cargo.toml Cargo.lock ./

# Create dummy main.rs to cache dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs

# Build dependencies
RUN cargo build --release && rm -rf src

# Copy source code
COPY src ./src

# Build the application
RUN touch src/main.rs && cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libsasl2-2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/market-intel-core-engine /usr/local/bin/

# Expose port
EXPOSE 50052

# Run the application
CMD ["market-intel-core-engine"]
