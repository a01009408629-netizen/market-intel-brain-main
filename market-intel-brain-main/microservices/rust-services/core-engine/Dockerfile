# Multi-stage build for Rust Core Engine
FROM rust:latest-slim AS builder

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

COPY Cargo.toml Cargo.lock ./

RUN mkdir -p src && \
    echo 'fn main() {}' > src/main.rs && \
    echo 'pub fn placeholder() {}' > src/lib.rs

RUN cargo build --release && rm -rf src

COPY src ./src

RUN touch src/main.rs src/lib.rs && \
    cargo build --release

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

COPY --from=builder /app/target/release/core-engine /usr/local/bin/

EXPOSE 50052

CMD ["core-engine"]