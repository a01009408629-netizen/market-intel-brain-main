# Multi-stage build for Go API Gateway
FROM golang:1.21-alpine as builder

# Install build dependencies
RUN apk add --no-cache git

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Copy proto files
COPY ../../proto ./proto

# Generate gRPC code
RUN go generate ./...

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o api-gateway ./cmd/api-gateway

# Runtime stage
FROM alpine:latest

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

# Set permissions
RUN chown -R apigateway:apigateway /app
RUN chmod +x /usr/local/bin/api-gateway

# Switch to non-root user
USER apigateway

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Set environment variables
ENV GIN_MODE=release
ENV PORT=8080
ENV GRPC_PORT=8081

# Run the application
CMD ["api-gateway"]
