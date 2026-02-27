# Multi-stage build for Go API Gateway with Protocol Buffer Generation
FROM golang:1.22-alpine as builder

# Install build dependencies and Protocol Buffer tools
RUN apk add --no-cache \
    git \
    protobuf \
    protobuf-dev \
    curl

# Install protoc-gen-go and protoc-gen-go-grpc
RUN go install \
    google.golang.org/protobuf/cmd/protoc-gen-go@latest \
    google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Copy proto files from both locations
RUN mkdir -p /tmp/proto
COPY microservices/proto/ /tmp/proto/
COPY src/schemas/ /tmp/proto/ 2>/dev/null || true

# Generate protocol buffers
RUN echo "Generating protocol buffers..." && \
    mkdir -p pb && \
    protoc --go_out=. --go-grpc_out=. --go_opt=paths=source_relative \
        /tmp/proto/*.proto \
        /tmp/proto/versions/v1/*.proto && \
    echo "Protocol buffers generated successfully"

# Download dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Copy source code including generated pb files
COPY . .

# Build application with stripped debug info to reduce binary size
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -a -installsuffix cgo -o api-gateway ./cmd/api-gateway

# Runtime stage
FROM alpine:3.19

# Install runtime dependencies
RUN apk --no-cache add ca-certificates tzdata

# Create app user
RUN addgroup -g 1001 -S apigateway && \
    adduser -u 1001 -S apigateway -G apigateway

WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/api-gateway /usr/local/bin/api-gateway

# Copy configuration files and generated pb files
COPY --from=builder /app/config ./config
COPY --from=builder /app/pb ./pb

# Set permissions for config directory
RUN chown -R apigateway:apigateway /app
RUN chmod +x /usr/local/bin/api-gateway

# Switch to non-root user
USER apigateway

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Set environment variables efficiently
ENV GIN_MODE=release \
    PORT=8080 \
    GRPC_PORT=8081

# Run application
CMD ["api-gateway"]
