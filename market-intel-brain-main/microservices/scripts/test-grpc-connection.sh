#!/bin/bash

# Test gRPC connection between Go API Gateway and Rust Core Engine

set -e

echo "🔧 Testing gRPC connection..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if services are running
check_service() {
    local service_name=$1
    local port=$2
    
    if nc -z localhost $port 2>/dev/null; then
        print_status "$service_name is running on port $port"
        return 0
    else
        print_warning "$service_name is not running on port $port"
        return 1
    fi
}

# Test Core Engine health
test_core_engine_health() {
    print_status "Testing Core Engine health check..."
    
    # Use grpcurl if available, otherwise use a simple HTTP check
    if command -v grpcurl &> /dev/null; then
        if grpcurl -plaintext localhost:50052 market_intel.core_engine.CoreEngineService/HealthCheck; then
            print_status "✅ Core Engine gRPC health check successful!"
            return 0
        else
            print_error "❌ Core Engine gRPC health check failed!"
            return 1
        fi
    else
        print_warning "grpcurl not found, skipping gRPC health check"
        return 0
    fi
}

# Test API Gateway health
test_api_gateway_health() {
    print_status "Testing API Gateway health check..."
    
    if curl -s http://localhost:8080/health > /dev/null; then
        print_status "✅ API Gateway health check successful!"
        
        # Test the ping endpoint
        if curl -s http://localhost:8080/ping > /dev/null; then
            print_status "✅ API Gateway ping endpoint working!"
        else
            print_warning "⚠️ API Gateway ping endpoint not working"
        fi
        
        # Test the Core Engine ping endpoint
        if curl -s http://localhost:8080/ping/core-engine > /dev/null; then
            print_status "✅ API Gateway → Core Engine ping successful!"
            return 0
        else
            print_warning "⚠️ API Gateway → Core Engine ping not working"
            return 1
        fi
    else
        print_error "❌ API Gateway health check failed!"
        return 1
    fi
}

# Main test flow
main() {
    print_status "Starting gRPC connection tests..."
    
    # Check if services are running
    core_engine_running=false
    api_gateway_running=false
    
    if check_service "Core Engine" 50052; then
        core_engine_running=true
    fi
    
    if check_service "API Gateway" 8080; then
        api_gateway_running=true
    fi
    
    # Run tests based on what's running
    if [ "$core_engine_running" = true ]; then
        test_core_engine_health
    else
        print_warning "Skipping Core Engine tests - service not running"
    fi
    
    if [ "$api_gateway_running" = true ]; then
        test_api_gateway_health
    else
        print_warning "Skipping API Gateway tests - service not running"
    fi
    
    # Summary
    echo ""
    print_status "Test Summary:"
    echo "  Core Engine: $([ "$core_engine_running" = true ] && echo "✅ Running" || echo "❌ Not Running")"
    echo "  API Gateway: $([ "$api_gateway_running" = true ] && echo "✅ Running" || echo "❌ Not Running")"
    
    if [ "$core_engine_running" = true ] && [ "$api_gateway_running" = true ]; then
        print_status "🎉 All services are running and connected!"
        exit 0
    else
        print_warning "Some services are not running. Start them with:"
        echo "  Core Engine: cd rust-services/core-engine && cargo run"
        echo "  API Gateway: cd go-services/api-gateway && go run cmd/api-gateway/main.go"
        exit 1
    fi
}

# Install dependencies if needed
if ! command -v nc &> /dev/null; then
    print_warning "netcat not found, installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y netcat-openbsd
    elif command -v brew &> /dev/null; then
        brew install netcat
    else
        print_warning "Cannot install netcat automatically. Please install it manually."
    fi
fi

if ! command -v curl &> /dev/null; then
    print_warning "curl not found, please install it for HTTP testing"
fi

# Run main function
main "$@"
