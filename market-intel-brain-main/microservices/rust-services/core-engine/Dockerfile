# Multi-stage build for Rust Core Engine
FROM rust:1.80-bookworm AS builder

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    build-essential \
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

WORKDIR /app

COPY --from=builder /app/target/release/core-engine /usr/local/bin/

EXPOSE 50052

CMD ["core-engine"]