#!/bin/bash

# Generate protobuf code for Rust and Go services

set -e

echo "🔧 Generating protobuf code..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_ROOT/proto"

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "❌ protoc is not installed. Please install Protocol Buffers compiler."
    echo "Visit: https://grpc.io/docs/protoc-installation/"
    exit 1
fi

# Check if Go plugins are installed
if ! command -v protoc-gen-go &> /dev/null; then
    echo "📦 Installing Go protobuf plugins..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
fi

# Generate Go code
echo "🐹 Generating Go protobuf code..."
cd "$PROJECT_ROOT"

# Create proto directories for Go services
mkdir -p go-services/api-gateway/proto
mkdir -p go-services/auth-service/proto

# Generate for API Gateway
protoc \
    --go_out=go-services/api-gateway/proto \
    --go_opt=paths=source_relative \
    --go-grpc_out=go-services/api-gateway/proto \
    --go-grpc_opt=paths=source_relative \
    --proto_path="$PROTO_DIR" \
    "$PROTO_DIR"/*.proto

# Copy generated files to the correct location
cp -r go-services/api-gateway/proto/github.com/market-intel/api-gateway/proto/* go-services/api-gateway/proto/ 2>/dev/null || true
rm -rf go-services/api-gateway/proto/github.com

echo "✅ Go protobuf code generated successfully!"

# Generate Rust code (build.rs will handle this)
echo "🦀 Rust protobuf code will be generated during build..."

echo "🎉 Protobuf generation complete!"
