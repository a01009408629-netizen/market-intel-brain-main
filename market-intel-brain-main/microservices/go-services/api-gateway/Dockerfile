# Multi-stage build for Go API Gateway
FROM golang:1.22-alpine as builder

# Install build dependencies
RUN apk add --no-cache git

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Copy source code (Assumes gRPC code is pre-generated)
COPY . .

# Build the application with stripped debug info to reduce binary size
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

# Copy configuration files
COPY --from=builder /app/config ./config

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

# Run the application
CMD ["api-gateway"]