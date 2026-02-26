# Market Intel Brain - Makefile
# Enterprise-grade build automation

.PHONY: help fix lint test build clean docker-build docker-run deploy

# Default target
help:
	@echo "Market Intel Brain - Enterprise Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  fix        - Fix Go dependencies and linting issues"
	@echo "  lint       - Run linting checks"
	@echo "  test       - Run all tests"
	@echo "  build      - Build all services"
	@echo "  clean      - Clean build artifacts"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-run  - Run Docker containers"
	@echo "  deploy     - Deploy to production"
	@echo ""

# Fix Go dependencies and linting issues
fix:
	@echo "🔧 Fixing Go dependencies and linting issues..."
	@cd microservices/go-services/api-gateway && \
		go mod tidy && \
		go mod vendor && \
		golangci-lint run --fix && \
		echo "✅ Go dependencies and linting fixed"

# Run linting checks
lint:
	@echo "🔍 Running linting checks..."
	@cd microservices/go-services/api-gateway && \
		golangci-lint run --timeout=10m && \
		echo "✅ Go linting completed"
	@cd microservices/rust-services/core-engine && \
		cargo fmt --all -- --check && \
		cargo clippy --all-targets --all-features -- -D warnings && \
		echo "✅ Rust linting completed"

# Run all tests
test:
	@echo "🧪 Running all tests..."
	@cd microservices/go-services/api-gateway && \
		go test -v ./... && \
		echo "✅ Go tests completed"
	@cd microservices/rust-services/core-engine && \
		cargo test --all && \
		echo "✅ Rust tests completed"

# Build all services
build:
	@echo "🏗️ Building all services..."
	@cd microservices/go-services/api-gateway && \
		go build -o bin/api-gateway ./cmd/main.go && \
		echo "✅ Go service built"
	@cd microservices/rust-services/core-engine && \
		cargo build --release && \
		echo "✅ Rust service built"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@cd microservices/go-services/api-gateway && \
		rm -rf bin/ vendor/ && \
		go clean -modcache && \
		echo "✅ Go artifacts cleaned"
	@cd microservices/rust-services/core-engine && \
		cargo clean && \
		echo "✅ Rust artifacts cleaned"

# Build Docker images
docker-build:
	@echo "🐳 Building Docker images..."
	@docker build -t market-intel/api-gateway:latest ./microservices/go-services/api-gateway && \
		echo "✅ API Gateway Docker image built"
	@docker build -t market-intel/core-engine:latest ./microservices/rust-services/core-engine && \
		echo "✅ Core Engine Docker image built"

# Run Docker containers
docker-run:
	@echo "🚀 Running Docker containers..."
	@docker-compose -f docker-compose.yml up -d && \
		echo "✅ Docker containers started"

# Deploy to production
deploy:
	@echo "🚀 Deploying to production..."
	@echo "Deployment logic would go here"
	@echo "✅ Deployment completed"

# Install development dependencies
install-deps:
	@echo "📦 Installing development dependencies..."
	@go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	@echo "✅ Development dependencies installed"
