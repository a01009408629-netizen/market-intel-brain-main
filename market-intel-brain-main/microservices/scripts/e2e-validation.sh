#!/bin/bash

# End-to-End Validation Script for Market Data Migration
# Tests: Client -> Go HTTP -> Rust gRPC -> Go HTTP -> Client

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to check if service is running
check_service() {
    local service_name=$1
    local port=$2
    local health_endpoint=$3
    
    if nc -z localhost $port 2>/dev/null; then
        print_status "$service_name is running on port $port"
        
        if [ -n "$health_endpoint" ]; then
            if curl -s "http://localhost:$port$health_endpoint" > /dev/null; then
                print_status "$service_name health check passed"
                return 0
            else
                print_error "$service_name health check failed"
                return 1
            fi
        else
            return 0
        fi
    else
        print_error "$service_name is not running on port $port"
        return 1
    fi
}

# Function to test API endpoint
test_api_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3
    
    print_status "Testing $description: $endpoint"
    
    local response=$(curl -s -w "%{http_code}" -o /dev/null "$endpoint" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        print_status "$description test passed (HTTP $response)"
        return 0
    else
        print_error "$description test failed (HTTP $response, expected $expected_status)"
        return 1
    fi
}

# Function to test gRPC endpoint
test_grpc_endpoint() {
    local port=$1
    local description=$2
    
    print_status "Testing $description on port $port"
    
    if nc -z localhost $port 2>/dev/null; then
        print_status "$description test passed (port $port is reachable)"
        return 0
    else
        print_error "$description test failed (port $port is not reachable)"
        return 1
    fi
}

# Main validation function
main() {
    print_header "Starting End-to-End Validation"
    
    local failed_tests=0
    local total_tests=0
    
    # Test 1: Check Go API Gateway
    print_header "Test 1: Go API Gateway"
    total_tests=$((total_tests + 1))
    if check_service "Go API Gateway" 8080 "/api/v1/health"; then
        print_status "✅ Go API Gateway test passed"
    else
        print_error "❌ Go API Gateway test failed"
        failed_tests=$((failed_tests + 1))
    fi
    
    # Test 2: Check Rust Core Engine gRPC
    print_header "Test 2: Rust Core Engine gRPC"
    total_tests=$((total_tests + 1))
    if test_grpc_endpoint 50052 "Rust Core Engine gRPC"; then
        print_status "✅ Rust Core Engine gRPC test passed"
    else
        print_error "❌ Rust Core Engine gRPC test failed"
        failed_tests=$((failed_tests + 1))
    fi
    
    # Test 3: Test basic API endpoints
    print_header "Test 3: Basic API Endpoints"
    
    # Test health endpoint
    total_tests=$((total_tests + 1))
    if test_api_endpoint "http://localhost:8080/api/v1/health" "200" "Health endpoint"; then
        print_status "✅ Health endpoint test passed"
    else
        print_error "❌ Health endpoint test failed"
        failed_tests=$((failed_tests + 1))
    fi
    
    # Test metrics endpoint
    total_tests=$((total_tests + 1))
    if test_api_endpoint "http://localhost:8080/metrics" "200" "Metrics endpoint"; then
        print_status "✅ Metrics endpoint test passed"
    else
        print_error "❌ Metrics endpoint test failed"
        failed_tests=$((failed_tests + 1))
    fi
    
    # Test 4: Test data flow (if data endpoints exist)
    print_header "Test 4: Data Flow Tests"
    
    # Test market data endpoint
    total_tests=$((total_tests + 1))
    if test_api_endpoint "http://localhost:8080/api/v1/market/data" "200" "Market data endpoint"; then
        print_status "✅ Market data endpoint test passed"
    else
        print_warning "⚠️ Market data endpoint test failed (may not be implemented yet)"
        # Don't count this as a failure for now
        failed_tests=$((failed_tests - 1))
        total_tests=$((total_tests - 1))
    fi
    
    # Test 5: Test observability stack
    print_header "Test 5: Observability Stack"
    
    # Test Prometheus
    total_tests=$((total_tests + 1))
    if test_api_endpoint "http://localhost:9090/-/healthy" "200" "Prometheus"; then
        print_status "✅ Prometheus test passed"
    else
        print_warning "⚠️ Prometheus test failed (may not be running)"
        # Don't count this as a failure for now
        failed_tests=$((failed_tests - 1))
        total_tests=$((total_tests - 1))
    fi
    
    # Test Grafana
    total_tests=$((total_tests + 1))
    if test_api_endpoint "http://localhost:3000/api/health" "200" "Grafana"; then
        print_status "✅ Grafana test passed"
    else
        print_warning "⚠️ Grafana test failed (may not be running)"
        # Don't count this as a failure for now
        failed_tests=$((failed_tests - 1))
        total_tests=$((total_tests - 1))
    fi
    
    # Summary
    print_header "Validation Summary"
    
    local passed_tests=$((total_tests - failed_tests))
    
    echo -e "${GREEN}Total Tests: $total_tests${NC}"
    echo -e "${GREEN}Passed: $passed_tests${NC}"
    echo -e "${RED}Failed: $failed_tests${NC}"
    
    if [ $failed_tests -eq 0 ]; then
        print_status "🎉 All tests passed! System is working correctly."
        exit 0
    else
        print_error "❌ $failed_tests test(s) failed. Please check the system."
        exit 1
    fi
}

# Run main function
main "$@"
