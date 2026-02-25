#!/bin/bash

# Development Post-start Script for Market Intel Brain
# Runs after services are started to perform additional setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="market-intel-brain"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Print functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Wait for services to be ready
wait_for_services() {
    print_header "Waiting for Services to be Ready"
    
    # Wait for API Gateway
    print_status "Waiting for API Gateway to be ready..."
    kubectl wait --for=condition=ready pod -l app=api-gateway -n $NAMESPACE --timeout=300s
    
    # Wait for Core Engine
    print_status "Waiting for Core Engine to be ready..."
    kubectl wait --for=condition=ready pod -l app=core-engine -n $NAMESPACE --timeout=300s
    
    # Wait for PostgreSQL
    print_status "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    
    # Wait for Redis
    print_status "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s
    
    print_status "All services are ready"
}

# Run health checks
run_health_checks() {
    print_header "Running Health Checks"
    
    # Check API Gateway health
    print_status "Checking API Gateway health..."
    local api_health=$(curl -s http://localhost:8080/api/v1/health || echo "failed")
    if [[ "$api_health" == *"healthy"* ]]; then
        print_status "✓ API Gateway is healthy"
    else
        print_warning "⚠ API Gateway health check failed: $api_health"
    fi
    
    # Check Core Engine health
    print_status "Checking Core Engine health..."
    local core_health=$(grpcurl -plaintext localhost:50052 || echo "failed")
    if [[ "$core_health" == *"healthy"* ]]; then
        print_status "✓ Core Engine is healthy"
    else
        print_warning "⚠ Core Engine health check failed: $core_health"
    fi
    
    # Check database connection
    print_status "Checking database connection..."
    if kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway health --db-check > /dev/null 2>&1; then
        print_status "✓ Database connection is healthy"
    else
        print_warning "⚠ Database connection check failed"
    fi
}

# Initialize development data
init_dev_data() {
    print_header "Initializing Development Data"
    
    # Create sample data
    print_status "Creating sample market data..."
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway seed-data --type=market --count=100 > /dev/null 2>&1
    
    print_status "Creating sample news data..."
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway seed-data --type=news --count=50 > /dev/null 2>&1
    
    print_status "Creating sample data sources..."
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway seed-data --type=sources --count=5 > /dev/null 2>&1
    
    print_status "Development data initialized"
}

# Set up monitoring and alerting
setup_monitoring() {
    print_header "Setting up Monitoring and Alerting"
    
    # Create monitoring dashboards
    print_status "Creating monitoring dashboards..."
    
    # Create Grafana dashboards
    kubectl exec deployment/grafana -n $NAMESPACE -- \
        grafana-cli --import "$PROJECT_ROOT/deploy/grafana/dashboards/market-intel.json" > /dev/null 2>&1
    
    # Set up alerting rules
    print_status "Setting up alerting rules..."
    
    # Create Prometheus alerting rules
    kubectl apply -f "$PROJECT_ROOT/deploy/monitoring/alerts.yml" > /dev/null 2>&1
    
    print_status "Monitoring and alerting set up"
}

# Run integration tests
run_integration_tests() {
    print_header "Running Integration Tests"
    
    # Run API Gateway integration tests
    print_status "Running API Gateway integration tests..."
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway test --integration --verbose > /dev/null 2>&1
    
    # Run Core Engine integration tests
    print_status "Running Core Engine integration tests..."
    kubectl exec deployment/core-engine -n $NAMESPACE -- \
        ./core-engine test --integration --verbose > /dev/null 2>&1
    
    print_status "Integration tests completed"
}

# Generate development documentation
generate_dev_docs() {
    print_header "Generating Development Documentation"
    
    # Generate API documentation
    print_status "Generating API documentation..."
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway docs --output /tmp/api-docs.html > /dev/null 2>&1
    
    # Copy documentation locally
    if [[ -f /tmp/api-docs.html ]]; then
        cp /tmp/api-docs.html "$PROJECT_ROOT/docs/api-dev.html"
        print_status "API documentation generated: $PROJECT_ROOT/docs/api-dev.html"
    fi
    
    # Generate architecture diagrams
    print_status "Generating architecture diagrams..."
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway arch-diagram --output /tmp/arch-diagram.png > /dev/null 2>&1
    
    if [[ -f /tmp/arch-diagram.png ]]; then
        cp /tmp/arch-diagram.png "$PROJECT_ROOT/docs/arch-diagram.png"
        print_status "Architecture diagram generated: $PROJECT_ROOT/docs/arch-diagram.png"
    fi
}

# Set up development tools
setup_dev_tools() {
    print_header "Setting up Development Tools"
    
    # Install development tools in containers
    print_status "Installing development tools..."
    
    # Install curl in API Gateway
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        apt-get update && apt-get install -y curl jq htop > /dev/null 2>&1
    
    # Install development tools in Core Engine
    kubectl exec deployment/core-engine -n $NAMESPACE -- \
        cargo install cargo-watch cargo-expand > /dev/null 2>&1
    
    print_status "Development tools installed"
}

# Create development shortcuts
create_dev_shortcuts() {
    print_header "Creating Development Shortcuts"
    
    # Create a shell script with common commands
    cat > "$PROJECT_ROOT/dev-shortcuts.sh" << 'EOF
#!/bin/bash

# Market Intel Brain Development Shortcuts

# Colors
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"

# Common commands
alias kdev="kubectl -n market-intel-brain"
alias klogs="kubectl logs -n market-intel-brain"
alias kexec="kubectl exec -it -n market-intel-brain"
alias kgp="kubectl get pods -n market-intel-brain"
alias ksvc="kubectl get services -n market-intel-brain"

# Service shortcuts
alias api="curl -s http://localhost:8080/api/v1"
alias health="curl -s http://localhost:8080/api/v1/health"
alias metrics="curl -s http://localhost:8080/api/v1/metrics"
alias grafana="open http://localhost:3000"
alias jaeger="open http://localhost:16686"
alias prometheus="open http://localhost:9090"

# Database shortcuts
alias db="kubectl exec -it deployment/postgres -n market-intel-brain -- psql"
alias redis="kubectl exec -it deployment/redis -n market-intel-brain -- redis-cli"

# Development commands
alias dev-up="./devops/scripts/dev-pre-start.sh setup"
alias dev-down="./devops/scripts/dev-pre-start.sh cleanup"
alias dev-restart="./devops/scripts/dev-pre-start.sh cleanup && ./devops/scripts/dev-pre-start.sh setup"
alias dev-status="kubectl get pods -n market-intel-brain"
alias dev-logs="kubectl logs -f deployment/api-gateway -n market-intel-brain --tail=50"
alias dev-test="./devops/scripts/dev-post-start.sh run_integration_tests"

# Tilt/Skaffold commands
alias tilt-up="tilt up"
alias tilt-down="tilt down"
alias tilt-status="tilt status"
alias skaffold-dev="skaffold dev"
alias skaffold-clean="skaffold clean"
alias skaffold-delete="skaffold delete"

# Help function
dev-help() {
    echo "Market Intel Brain Development Shortcuts"
    echo ""
    echo "Service Commands:"
    echo "  api      - API Gateway health check"
    echo "  health   - API Gateway health check"
    echo "  metrics  - API Gateway metrics"
    echo "  grafana  - Open Grafana dashboard"
    echo "  jaeger   - Open Jaeger UI"
    echo "  prometheus - Open Prometheus UI"
    echo ""
    echo "Database Commands:"
    echo "  db       - Connect to PostgreSQL"
    echo "  redis    - Connect to Redis"
    echo ""
    echo "Development Commands:"
    echo "  dev-up    - Set up development environment"
    echo "  dev-down  - Clean up development environment"
    echo "  dev-restart - Restart development environment"
    echo "  dev-status - Show pod status"
    echo "  dev-logs  - Show API Gateway logs"
    echo "  dev-test  - Run integration tests"
    echo ""
    echo "Tilt/Skaffold Commands:"
    echo "  tilt-up   - Start Tilt"
    echo "  tilt-down - Stop Tilt"
    echo "  skaffold-dev - Start Skaffold dev"
    echo "  skaffold-clean - Clean Skaffold cache"
}

# Show help if no arguments
if [[ $# -eq 0 ]]; then
    dev-help
fi
EOF
    
    chmod +x "$PROJECT_ROOT/dev-shortcuts.sh"
    print_status "Development shortcuts created: $PROJECT_ROOT/dev-shortcuts.sh"
    
    # Create a Makefile for common development tasks
    cat > "$PROJECT_ROOT/Makefile.dev" << 'EOF
# Market Intel Brain Development Makefile

.PHONY: help dev-setup dev-up dev-down dev-restart dev-status dev-logs dev-test dev-clean

# Help
help:
	@echo "Market Intel Brain Development Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  dev-setup    - Set up development environment"
	@echo "  dev-up      - Start development environment"
	@echo "  dev-down    - Clean up development environment"
	@echo "  dev-restart - Restart development environment"
	@echo "  dev-status  - Show pod status"
	@echo "  dev-logs    - Show API Gateway logs"
	@echo "  dev-test    - Run integration tests"
	@echo "  dev-clean   - Clean up development environment"

# Development setup
dev-setup: dev-up

# Start development environment
dev-up:
	@echo "Starting development environment..."
	@./devops/scripts/dev-pre-start.sh setup

# Clean up development environment
dev-down:
	@echo "Cleaning up development environment..."
	@./devops/scripts/dev-pre-start.sh cleanup

# Restart development environment
dev-restart: dev-down dev-up

# Show pod status
dev-status:
	@echo "Pod status:"
	@kubectl get pods -n market-intel-brain

# Show API Gateway logs
dev-logs:
	@echo "API Gateway logs:"
	@kubectl logs -f deployment/api-gateway -n market-intel-brain --tail=100

# Run integration tests
dev-test:
	@echo "Running integration tests..."
	@./devops/scripts/dev-post-start.sh run_integration_tests

# Clean up development environment
dev-clean:
	@echo "Cleaning up development environment..."
	@./devops/scripts/dev-pre-start.sh cleanup
	@echo "Removing generated files..."
	@rm -f dev-shortcuts.sh Makefile.dev

# Quick test
quick-test:
	@echo "Running quick health check..."
	@curl -s http://localhost:8080/api/v1/health | jq .
EOF
    
    print_status "Development Makefile created: $PROJECT_ROOT/Makefile.dev"
}

# Display development status
show_dev_status() {
    print_header "Development Environment Status"
    
    echo "Namespace: $NAMESPACE"
    echo ""
    echo "Pods:"
    kubectl get pods -n $NAMESPACE -o wide
    echo ""
    echo "Services:"
    kubectl get services -n $NAMESPACE
    echo ""
    echo "Port Forwarding:"
    if [[ -f "$PROJECT_ROOT/.port_forward_pids" ]]; then
        echo "Active port forwarding processes:"
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "  ✓ $pid (running)"
            else
                echo "  ✗ $pid (not running)"
            fi
        done < "$PROJECT_ROOT/.port_forward_pids"
    fi
}

# Main execution
main() {
    case "${1:-post-start}" in
        "post-start")
            wait_for_services
            run_health_checks
            init_dev_data
            setup_monitoring
            setup_dev_tools
            create_dev_shortcuts
            show_dev_status
            ;;
        "health-check")
            run_health_checks
            ;;
        "init-data")
            init_dev_data
            ;;
        "integration-tests")
            run_integration_tests
            ;;
        "monitoring")
            setup_monitoring
            ;;
        "tools")
            setup_dev_tools
            ;;
        "shortcuts")
            create_dev_shortcuts
            ;;
        "docs")
            generate_dev_docs
            ;;
        "status")
            show_dev_status
            ;;
        "help"|"-h"|"--help")
            echo "Market Intel Brain Development Post-start Script"
            echo ""
            echo "Usage: $0 {post-start|health-check|init-data|integration-tests|monitoring|tools|shortcuts|docs|status|help}"
            echo ""
            echo "Commands:"
            echo "  post-start       - Complete post-start setup"
            echo "  health-check    - Run health checks"
            echo "  init-data       - Initialize development data"
            echo "  integration-tests - Run integration tests"
            echo "  monitoring       - Set up monitoring and alerting"
            echo "  tools          - Install development tools"
            echo "  shortcuts       - Create development shortcuts"
            echo "  docs           - Generate development documentation"
            echo "  status         - Show development environment status"
            echo ""
            echo "Examples:"
            echo "  $0 post-start"
            echo "  $0 health-check"
            echo "  $0 status"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
