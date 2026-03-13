# Multi-stage build for Rust Core Engine
# Build context: market-intel-brain-main/ (inner directory)
FROM rust:1.85-bookworm AS builder

RUN apt-get update && apt-get install -y \
    libsasl2-dev pkg-config libssl-dev libpq-dev \
    protobuf-compiler libclang-dev clang cmake \
    build-essential curl libcurl4-openssl-dev \
    librdkafka-dev libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── 1. Copy Cargo manifests ──────────────────────────────────────────────────
COPY microservices/rust-services/Cargo.toml \
     ./microservices/rust-services/Cargo.toml
COPY microservices/rust-services/core-engine/Cargo.toml \
     ./microservices/rust-services/core-engine/Cargo.toml
COPY microservices/rust-services/core-engine/Cargo.lock \
     ./microservices/rust-services/core-engine/Cargo.lock

# ── 2. Copy proto files (needed by real build.rs at compile time) ────────────
COPY microservices/proto ./microservices/proto

# ── 3. Copy REAL build.rs BEFORE the dummy build ─────────────────────────────
#    This way cargo runs the real build.rs (proto generation) during caching
COPY microservices/rust-services/core-engine/build.rs \
     ./microservices/rust-services/core-engine/build.rs

# ── 4. Dummy source files → cache dependencies ───────────────────────────────
RUN mkdir -p microservices/rust-services/core-engine/src && \
    echo 'fn main() {}' > microservices/rust-services/core-engine/src/main.rs && \
    echo 'pub fn placeholder() {}' > microservices/rust-services/core-engine/src/lib.rs

RUN cd microservices/rust-services && cargo build --release

# ── 5. Copy real source files ────────────────────────────────────────────────
RUN rm microservices/rust-services/core-engine/src/main.rs \
       microservices/rust-services/core-engine/src/lib.rs

COPY microservices/rust-services/core-engine/src \
     ./microservices/rust-services/core-engine/src

# ── 6. Build real binary (proto already generated, deps cached) ───────────────
RUN cd microservices/rust-services && \
    touch core-engine/src/main.rs core-engine/src/lib.rs && \
    cargo build --release

# ── Runtime Stage ────────────────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libsasl2-2 libssl3 libpq5 librdkafka1 libzstd1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/microservices/rust-services/target/release/core-engine \
     /usr/local/bin/

EXPOSE 50052
CMD ["core-engine"]
