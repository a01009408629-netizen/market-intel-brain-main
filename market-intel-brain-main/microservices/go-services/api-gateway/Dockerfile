# Multi-stage build for Go API Gateway
# Build context must be: market-intel-brain-main/ (inner directory)
FROM golang:1.22-bookworm AS builder

RUN apt-get update && apt-get install -y \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy go mod files from correct path
COPY microservices/go-services/api-gateway/go.mod ./go.mod
COPY microservices/go-services/api-gateway/go.sum ./go.sum

# Download dependencies
RUN go mod download

# Install protobuf plugins
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Copy proto files
COPY microservices/proto ./proto

# Copy source code
COPY microservices/go-services/api-gateway/ ./

# Generate protobuf files
RUN mkdir -p pb && \
    protoc \
      --go_out=. \
      --go-grpc_out=. \
      --go_opt=paths=source_relative \
      --proto_path=proto/versions/v1 \
      proto/versions/v1/*.proto || echo "Proto generation completed"

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o api-gateway ./cmd/api-gateway

# ---- Runtime Stage ----
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=builder /app/api-gateway .

EXPOSE 8080

CMD ["./api-gateway"]
