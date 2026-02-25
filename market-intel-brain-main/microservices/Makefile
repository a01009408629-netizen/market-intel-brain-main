# Market Intel Brain Microservices Makefile
# Provides commands for development, testing, deployment, and load testing

.PHONY: help build run stop clean test lint fmt docker-build docker-run docker-stop
.PHONY: start-prod start-dev load-test profile collect-results health-check
.PHONY: install-deps install-k6 install-tools check-deps

# Default target
help: ## Show this help message
	@echo "Market Intel Brain Microservices Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Commands
install-deps: ## Install all dependencies (Go, Rust, k6)
	@echo "Installing dependencies..."
	@echo "Installing Go dependencies..."
	cd go-services/api-gateway && go mod download
	@echo "Installing Rust dependencies..."
	cd rust-services/core-engine && cargo fetch
	@echo "Installing k6 for load testing..."
	@if ! command -v k6 &> /dev/null; then \
		echo "Installing k6..."; \
		if [[ "$$OSTYPE" == "darwin"* ]]; then \
			brew install k6; \
		elif [[ "$$OSTYPE" == "linux-gnu"* ]]; then \
			sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 \
			echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list \
			sudo apt-get update \
			sudo apt-get install k6; \
		fi; \
	fi
	@echo "Dependencies installed successfully!"

install-tools: ## Install development tools
	@echo "Installing development tools..."
	@echo "Installing Go tools..."
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	go install github.com/air-verse/air@latest
	@echo "Installing Rust tools..."
	rustup component add rustfmt clippy
	cargo install cargo-watch cargo-tarpaulin
	@echo "Installing buf for protobuf..."
	go install github.com/bufbuild/buf/cmd/buf@latest
	@echo "Development tools installed successfully!"

check-deps: ## Check if all dependencies are installed
	@echo "Checking dependencies..."
	@command -v go >/dev/null 2>&1 || { echo "Go is not installed"; exit 1; }
	@command -v cargo >/dev/null 2>&1 || { echo "Rust is not installed"; exit 1; }
	@command -v docker >/dev/null 2>&1 || { echo "Docker is not installed"; exit 1; }
	@command -v k6 >/dev/null 2>&1 || { echo "k6 is not installed"; exit 1; }
	@echo "All dependencies are installed!"

# Build Commands
build: ## Build all services
	@echo "Building Go API Gateway..."
	cd go-services/api-gateway && go build -o bin/api-gateway ./cmd/api-gateway
	@echo "Building Rust Core Engine..."
	cd rust-services/core-engine && cargo build --release
	@echo "All services built successfully!"

build-debug: ## Build all services in debug mode
	@echo "Building Go API Gateway (debug)..."
	cd go-services/api-gateway && go build -o bin/api-gateway-debug ./cmd/api-gateway
	@echo "Building Rust Core Engine (debug)..."
	cd rust-services/core-engine && cargo build
	@echo "All services built successfully in debug mode!"

# Docker Commands
docker-build: ## Build Docker images for all services
	@echo "Building Docker images..."
	docker-compose build
	@echo "Docker images built successfully!"

docker-run: ## Start all services with Docker Compose
	@echo "Starting services with Docker Compose..."
	docker-compose up -d
	@echo "Services started successfully!"

docker-stop: ## Stop all services
	@echo "Stopping services..."
	docker-compose down
	@echo "Services stopped successfully!"

docker-logs: ## Show Docker logs
	@echo "Showing Docker logs..."
	docker-compose logs -f

# Development Commands
start-dev: ## Start all services in development mode
	@echo "Starting services in development mode..."
	@echo "Starting observability stack..."
	docker-compose -f docker-compose-observability.yml up -d
	@echo "Starting Rust Core Engine..."
	cd rust-services/core-engine && cargo run &
	@echo "Starting Go API Gateway..."
	cd go-services/api-gateway && air &
	@echo "All services started in development mode!"

start-prod: ## Start all services in production mode
	@echo "Starting services in production mode..."
	@echo "Starting observability stack..."
	docker-compose -f docker-compose-observability.yml up -d
	@echo "Starting Rust Core Engine..."
	cd rust-services/core-engine && cargo run --release &
	@echo "Starting Go API Gateway..."
	cd go-services/api-gateway && ./bin/api-gateway &
	@echo "All services started in production mode!"

stop: ## Stop all running services
	@echo "Stopping all services..."
	@pkill -f "cargo run" || true
	@pkill -f "api-gateway" || true
	@pkill -f "air" || true
	docker-compose -f docker-compose-observability.yml down
	@echo "All services stopped!"

restart: stop start-prod ## Restart all services

# Testing Commands
test: ## Run all tests
	@echo "Running Go tests..."
	cd go-services/api-gateway && go test -v -race ./...
	@echo "Running Rust tests..."
	cd rust-services/core-engine && cargo test
	@echo "All tests completed!"

test-coverage: ## Run tests with coverage
	@echo "Running Go tests with coverage..."
	cd go-services/api-gateway && go test -v -race -coverprofile=coverage.out ./...
	@echo "Running Rust tests with coverage..."
	cd rust-services/core-engine && cargo tarpaulin --out Xml --output-dir ./coverage
	@echo "Coverage reports generated!"

lint: ## Run all linting
	@echo "Running Go linting..."
	cd go-services/api-gateway && golangci-lint run
	@echo "Running Rust linting..."
	cd rust-services/core-engine && cargo clippy --all-targets --all-features -- -D warnings
	@echo "Linting completed!"

fmt: ## Format all code
	@echo "Formatting Go code..."
	cd go-services/api-gateway && go fmt ./...
	@echo "Formatting Rust code..."
	cd rust-services/core-engine && cargo fmt
	@echo "Code formatted successfully!"

check: fmt lint test ## Run all checks (format, lint, test)

# Health Check Commands
health-check: ## Check health of all services
	@echo "Checking service health..."
	@echo "Checking Go API Gateway..."
	@curl -f http://localhost:8080/api/v1/health || echo "API Gateway is not healthy"
	@echo "Checking Rust Core Engine..."
	@curl -f http://localhost:50052 || echo "Core Engine is not healthy"
	@echo "Checking observability services..."
	@curl -f http://localhost:16686 || echo "Jaeger is not healthy"
	@curl -f http://localhost:9090 || echo "Prometheus is not healthy"
	@curl -f http://localhost:3000 || echo "Grafana is not healthy"
	@echo "Health check completed!"

wait-ready: ## Wait for all services to be ready
	@echo "Waiting for services to be ready..."
	@timeout 300 bash -c 'until curl -f http://localhost:8080/api/v1/health; do sleep 5; done'
	@timeout 300 bash -c 'until curl -f http://localhost:50052; do sleep 5; done'
	@echo "All services are ready!"

# Load Testing Commands
load-test: ## Run load test with k6
	@echo "Starting load test..."
	@echo "Make sure all services are running with 'make start-prod'"
	@echo "Waiting for services to be ready..."
	$(MAKE) wait-ready
	@echo "Running k6 load test..."
	k6 run --out json=load-test-results.json load-testing/k6-load-test.js
	@echo "Load test completed!"

load-test-light: ## Run light load test (100 users)
	@echo "Starting light load test..."
	@echo "Waiting for services to be ready..."
	$(MAKE) wait-ready
	@echo "Running k6 light load test..."
	k6 run --out json=load-test-results-light.json \
		--vus 100 \
		--duration 5m \
		load-testing/k6-load-test.js
	@echo "Light load test completed!"

load-test-heavy: ## Run heavy load test (2000 users)
	@echo "Starting heavy load test..."
	@echo "Waiting for services to be ready..."
	$(MAKE) wait-ready
	@echo "Running k6 heavy load test..."
	k6 run --out json=load-test-results-heavy.json \
		--vus 2000 \
		--duration 10m \
		load-testing/k6-load-test.js
	@echo "Heavy load test completed!"

# Profiling Commands
profile: ## Start profiling with pprof
	@echo "Starting profiling..."
	@echo "Make sure the Go API Gateway is running with profiling enabled"
	@echo "Profiling endpoints available at:"
	@echo "  - CPU Profile: http://localhost:8080/debug/pprof/profile?seconds=30"
	@echo "  - Heap Profile: http://localhost:8080/debug/pprof/heap"
	@echo "  - Goroutine Profile: http://localhost:8080/debug/pprof/goroutine"
	@echo "  - Trace: http://localhost:8080/debug/pprof/trace?seconds=5"
	@echo "Use 'go tool pprof' to analyze the profiles"

profile-cpu: ## Collect CPU profile for 30 seconds
	@echo "Collecting CPU profile for 30 seconds..."
	curl -s "http://localhost:8080/debug/pprof/profile?seconds=30" > cpu-profile.pprof
	@echo "CPU profile saved to cpu-profile.pprof"
	@echo "Analyze with: go tool pprof cpu-profile.pprof"

profile-heap: ## Collect heap profile
	@echo "Collecting heap profile..."
	curl -s "http://localhost:8080/debug/pprof/heap" > heap-profile.pprof
	@echo "Heap profile saved to heap-profile.pprof"
	@echo "Analyze with: go tool pprof heap-profile.pprof"

profile-goroutine: ## Collect goroutine profile
	@echo "Collecting goroutine profile..."
	curl -s "http://localhost:8080/debug/pprof/goroutine" > goroutine-profile.pprof
	@echo "Goroutine profile saved to goroutine-profile.pprof"
	@echo "Analyze with: go tool pprof goroutine-profile.pprof"

profile-trace: ## Collect execution trace for 5 seconds
	@echo "Collecting execution trace for 5 seconds..."
	curl -s "http://localhost:8080/debug/pprof/trace?seconds=5" > trace.out
	@echo "Trace saved to trace.out"
	@echo "Analyze with: go tool trace trace.out"

profile-all: ## Collect all profiles
	@echo "Collecting all profiles..."
	$(MAKE) profile-cpu
	$(MAKE) profile-heap
	$(MAKE) profile-goroutine
	$(MAKE) profile-trace
	@echo "All profiles collected!"

# Results Collection Commands
collect-results: ## Collect and analyze load test results
	@echo "Collecting load test results..."
	@mkdir -p results
	@echo "Copying k6 results..."
	@if [ -f load-test-results.json ]; then cp load-test-results.json results/; fi
	@if [ -f load-test-results-light.json ]; then cp load-test-results-light.json results/; fi
	@if [ -f load-test-results-heavy.json ]; then cp load-test-results-heavy.json results/; fi
	@echo "Collecting profiling results..."
	@if [ -f cpu-profile.pprof ]; then cp cpu-profile.pprof results/; fi
	@if [ -f heap-profile.pprof ]; then cp heap-profile.pprof results/; fi
	@if [ -f goroutine-profile.pprof ]; then cp goroutine-profile.pprof results/; fi
	@if [ -f trace.out ]; then cp trace.out results/; fi
	@echo "Collecting metrics..."
	@curl -s http://localhost:9090/api/v1/query?query='up' > results/prometheus-metrics.json 2>/dev/null || true
	@echo "Results collected in results/ directory"

analyze-results: ## Analyze collected results
	@echo "Analyzing load test results..."
	@if [ -f results/load-test-results.json ]; then \
		echo "Load test results:"; \
		k6 metrics --output json results/load-test-results.json; \
	fi
	@echo "Analyzing profiles..."
	@if [ -f results/cpu-profile.pprof ]; then \
		echo "CPU Profile:"; \
		go tool pprof -text results/cpu-profile.pprof | head -20; \
	fi
	@if [ -f results/heap-profile.pprof ]; then \
		echo "Heap Profile:"; \
		go tool pprof -text results/heap-profile.pprof | head -20; \
	fi

# Performance Testing Workflow
perf-test: ## Complete performance testing workflow
	@echo "Starting complete performance testing workflow..."
	@echo "1. Starting services in production mode..."
	$(MAKE) start-prod
	@sleep 10
	@echo "2. Running health check..."
	$(MAKE) health-check
	@echo "3. Running light load test..."
	$(MAKE) load-test-light
	@echo "4. Collecting profiles..."
	$(MAKE) profile-all
	@echo "5. Running main load test..."
	$(MAKE) load-test
	@echo "6. Collecting results..."
	$(MAKE) collect-results
	@echo "7. Analyzing results..."
	$(MAKE) analyze-results
	@echo "Performance testing workflow completed!"

# Cleanup Commands
clean: ## Clean build artifacts and temporary files
	@echo "Cleaning build artifacts..."
	@rm -rf go-services/api-gateway/bin/
	@rm -rf go-services/api-gateway/coverage.out
	@rm -rf rust-services/core-engine/target/
	@rm -rf rust-services/core-engine/coverage/
	@rm -f *.pprof
	@rm -f *.out
	@rm -f load-test-results*.json
	@rm -rf results/
	@echo "Clean completed!"

clean-docker: ## Clean Docker images and containers
	@echo "Cleaning Docker resources..."
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f
	@echo "Docker cleanup completed!"

# Development Workflow
dev-setup: install-deps install-tools check-deps ## Complete development setup
	@echo "Development setup completed!"
	@echo "Run 'make start-dev' to start development services"

# Production Workflow
prod-setup: build docker-build ## Complete production setup
	@echo "Production setup completed!"
	@echo "Run 'make start-prod' to start production services"

# Quick Commands
quick-test: start-prod wait-ready load-test-light stop ## Quick performance test
	@echo "Quick performance test completed!"

quick-profile: start-prod wait-ready profile-cpu profile-heap stop ## Quick profiling
	@echo "Quick profiling completed!"

# Environment Variables
export GOMAXPROCS := $(shell nproc)
export RUST_LOG := info
export ENVIRONMENT := development
