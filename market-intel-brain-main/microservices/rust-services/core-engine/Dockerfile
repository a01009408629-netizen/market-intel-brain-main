# Multi-stage build for Rust Core Engine
# Build context must be: market-intel-brain-main/ (inner directory)
FROM rust:1.85-bookworm AS builder

RUN apt-get update && apt-get install -y \
    libsasl2-dev \
    pkg-config \
    libssl-dev \
    libpq-dev \
    protobuf-compiler \
    libclang-dev \
    clang \
    cmake \
    build-essential \
    curl \
    libcurl4-openssl-dev \
    librdkafka-dev \
    libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy workspace Cargo files
COPY microservices/rust-services/Cargo.toml ./microservices/rust-services/Cargo.toml

# Copy core-engine Cargo files
COPY microservices/rust-services/core-engine/Cargo.toml ./microservices/rust-services/core-engine/Cargo.toml
COPY microservices/rust-services/core-engine/Cargo.lock ./microservices/rust-services/core-engine/Cargo.lock

# Copy proto files (required by build.rs at compile time)
COPY microservices/proto ./microservices/proto

# Dummy build to cache dependencies
RUN mkdir -p microservices/rust-services/core-engine/src microservices/rust-services/core-engine/src/proto && \
    echo 'fn main() {}' > microservices/rust-services/core-engine/src/main.rs && \
    echo 'pub fn placeholder() {}' > microservices/rust-services/core-engine/src/lib.rs && \
    echo 'fn main() -> Result<(), Box<dyn std::error::Error>> { Ok(()) }' > microservices/rust-services/core-engine/build.rs && \
    cd microservices/rust-services && cargo build --release && \
    rm -rf core-engine/src core-engine/build.rs

# Copy real source code and build.rs
COPY microservices/rust-services/core-engine/src ./microservices/rust-services/core-engine/src
COPY microservices/rust-services/core-engine/build.rs ./microservices/rust-services/core-engine/build.rs

# Build the real binary
RUN cd microservices/rust-services && \
    touch core-engine/src/main.rs core-engine/src/lib.rs && \
    cargo build --release

# ---- Runtime Stage ----
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libsasl2-2 \
    libssl3 \
    libpq5 \
    librdkafka1 \
    libzstd1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/microservices/rust-services/target/release/core-engine /usr/local/bin/

EXPOSE 50052

CMD ["core-engine"]
