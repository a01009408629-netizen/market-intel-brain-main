# Multi-stage build for Go API Gateway
FROM golang:1.22-bookworm as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Install protobuf plugins
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Copy source code
COPY . .

# Generate protobuf files
RUN mkdir -p pb && \
    protoc --go_out=. --go-grpc_out=. --go_opt=paths=source_relative \
    ../proto/*.proto ../proto/versions/v1/*.proto

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o api-gateway ./cmd/api-gateway

# Runtime stage
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy binary from builder
COPY --from=builder /app/api-gateway .

# Expose port
EXPOSE 8080

# Run the application
CMD ["./api-gateway"]
