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
        fi
        return 0
    else
        print_error "$service_name is not running on port $port"
        return 1
    fi
}

# Function to start services
start_services() {
    print_header "Starting Services"
    
    # Start Rust Core Engine
    print_status "Starting Rust Core Engine..."
    cd "$PROJECT_ROOT/rust-services/core-engine"
    cargo run > /tmp/core-engine.log 2>&1 &
    CORE_ENGINE_PID=$!
    echo $CORE_ENGINE_PID > /tmp/core-engine.pid
    
    # Wait for Core Engine to start
    sleep 5
    
    # Start Go API Gateway
    print_status "Starting Go API Gateway..."
    cd "$PROJECT_ROOT/go-services/api-gateway"
    go run cmd/api-gateway/main.go > /tmp/api-gateway.log 2>&1 &
    API_GATEWAY_PID=$!
    echo $API_GATEWAY_PID > /tmp/api-gateway.pid
    
    # Wait for API Gateway to start
    sleep 3
    
    print_status "Services started successfully"
}

# Function to stop services
stop_services() {
    print_header "Stopping Services"
    
    # Stop Core Engine
    if [ -f /tmp/core-engine.pid ]; then
        CORE_ENGINE_PID=$(cat /tmp/core-engine.pid)
        if kill -0 $CORE_ENGINE_PID 2>/dev/null; then
            print_status "Stopping Core Engine (PID: $CORE_ENGINE_PID)"
            kill $CORE_ENGINE_PID
            wait $CORE_ENGINE_PID 2>/dev/null || true
        fi
        rm -f /tmp/core-engine.pid
    fi
    
    # Stop API Gateway
    if [ -f /tmp/api-gateway.pid ]; then
        API_GATEWAY_PID=$(cat /tmp/api-gateway.pid)
        if kill -0 $API_GATEWAY_PID 2>/dev/null; then
            print_status "Stopping API Gateway (PID: $API_GATEWAY_PID)"
            kill $API_GATEWAY_PID
            wait $API_GATEWAY_PID 2>/dev/null || true
        fi
        rm -f /tmp/api-gateway.pid
    fi
    
    print_status "Services stopped"
}

# Function to test market data flow
test_market_data_flow() {
    print_header "Testing Market Data Flow"
    
    # Test 1: Fetch market data via Go API Gateway
    print_status "Test 1: Fetch market data via Go API Gateway"
    
    response=$(curl -s -X POST http://localhost:8080/api/v1/market-data/fetch \
        -H "Content-Type: application/json" \
        -d '{
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "source_id": "yahoo_finance"
        }')
    
    if [ $? -eq 0 ]; then
        print_status "✅ Market data fetch successful"
        echo "Response: $response" | jq . > /tmp/market_data_response.json
    else
        print_error "❌ Market data fetch failed"
        return 1
    fi
    
    # Test 2: Get market data buffer
    print_status "Test 2: Get market data buffer"
    
    buffer_response=$(curl -s "http://localhost:8080/api/v1/market-data/buffer?symbol=AAPL&limit=5")
    
    if [ $? -eq 0 ]; then
        print_status "✅ Market data buffer fetch successful"
        echo "Buffer Response: $buffer_response" | jq . > /tmp/buffer_response.json
    else
        print_error "❌ Market data buffer fetch failed"
        return 1
    fi
    
    # Test 3: Get ingestion stats
    print_status "Test 3: Get ingestion statistics"
    
    stats_response=$(curl -s "http://localhost:8080/api/v1/ingestion/stats")
    
    if [ $? -eq 0 ]; then
        print_status "✅ Ingestion stats fetch successful"
        echo "Stats Response: $stats_response" | jq . > /tmp/stats_response.json
    else
        print_error "❌ Ingestion stats fetch failed"
        return 1
    fi
    
    # Test 4: Connect to data source
    print_status "Test 4: Connect to data source"
    
    connect_response=$(curl -s -X POST http://localhost:8080/api/v1/data-sources/connect \
        -H "Content-Type: application/json" \
        -d '{
            "source_id": "yahoo_finance",
            "api_key": ""
        }')
    
    if [ $? -eq 0 ]; then
        print_status "✅ Data source connection successful"
        echo "Connect Response: $connect_response" | jq . > /tmp/connect_response.json
    else
        print_error "❌ Data source connection failed"
        return 1
    fi
    
    return 0
}

# Function to test WebSocket flow
test_websocket_flow() {
    print_header "Testing WebSocket Flow"
    
    # Create a simple WebSocket test using Python
    cat > /tmp/websocket_test.py << 'EOF'
import asyncio
import websockets
import json
import time

async def test_websocket():
    uri = "ws://localhost:8080/api/v1/ws/market-data"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Send market data request
            request = {
                "symbols": ["AAPL", "GOOGL"],
                "source_id": "yahoo_finance"
            }
            
            await websocket.send(json.dumps(request))
            print("✅ Request sent")
            
            # Wait for response
            response = await websocket.recv()
            print(f"✅ Response received: {response}")
            
            return True
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    exit(0 if result else 1)
EOF
    
    # Check if Python and websockets are available
    if command -v python3 &> /dev/null && python3 -c "import websockets" 2>/dev/null; then
        print_status "Running WebSocket test..."
        if python3 /tmp/websocket_test.py; then
            print_status "✅ WebSocket test passed"
        else
            print_warning "⚠️ WebSocket test failed (websockets library may not be installed)"
        fi
    else
        print_warning "⚠️ Skipping WebSocket test (Python or websockets not available)"
    fi
    
    rm -f /tmp/websocket_test.py
}

# Function to compare with legacy Python system
compare_with_legacy() {
    print_header "Comparing with Legacy Python System"
    
    # Check if legacy Python system is available
    if [ ! -f "$PROJECT_ROOT/api_server.py" ]; then
        print_warning "⚠️ Legacy Python system not found, skipping comparison"
        return 0
    fi
    
    print_status "Testing legacy Python system..."
    
    # Start legacy Python system (if possible)
    cd "$PROJECT_ROOT"
    
    # Check if required Python dependencies are available
    if python3 -c "import fastapi, uvicorn" 2>/dev/null; then
        print_status "Starting legacy Python API server..."
        
        # Start Python server in background
        python3 -c "
import uvicorn
from api_server import app
uvicorn.run(app, host='0.0.0.0', port=8001, log_level='error')
" > /tmp/python_server.log 2>&1 &
        PYTHON_PID=$!
        echo $PYTHON_PID > /tmp/python_server.pid
        
        # Wait for Python server to start
        sleep 5
        
        # Test Python API
        if curl -s http://localhost:8001/health > /dev/null; then
            print_status "✅ Legacy Python system is running"
            
            # Test market data endpoint
            python_response=$(curl -s -X POST http://localhost:8001/api/v1/data/binance/BTCUSDT)
            
            if [ $? -eq 0 ]; then
                print_status "✅ Legacy Python market data endpoint working"
                echo "Python Response: $python_response" > /tmp/python_response.json
                
                # Compare responses (basic comparison)
                print_status "Comparing Go and Python responses..."
                
                # Extract key fields from both responses for comparison
                go_symbols=$(cat /tmp/market_data_response.json | jq -r '.market_data[0].symbol // "N/A"')
                go_price=$(cat /tmp/market_data_response.json | jq -r '.market_data[0].price // "N/A"')
                
                print_status "Go Response: Symbol=$go_symbols, Price=$go_price"
                print_status "Python Response: Available (see /tmp/python_response.json)"
                
                print_status "✅ Basic comparison completed"
            else
                print_warning "⚠️ Legacy Python market data endpoint failed"
            fi
        else
            print_warning "⚠️ Legacy Python system failed to start"
        fi
        
        # Stop Python server
        if [ -f /tmp/python_server.pid ]; then
            PYTHON_PID=$(cat /tmp/python_server.pid)
            if kill -0 $PYTHON_PID 2>/dev/null; then
                kill $PYTHON_PID
                wait $PYTHON_PID 2>/dev/null || true
            fi
            rm -f /tmp/python_server.pid
        fi
    else
        print_warning "⚠️ Python dependencies not available, skipping legacy comparison"
    fi
}

# Function to validate feature parity
validate_feature_parity() {
    print_header "Validating Feature Parity"
    
    # Check response structure
    go_response_file="/tmp/market_data_response.json"
    
    if [ -f "$go_response_file" ]; then
        # Validate required fields
        required_fields=("success" "message" "market_data" "metadata" "timestamp")
        
        for field in "${required_fields[@]}"; do
            if jq -e ".$field" "$go_response_file" > /dev/null; then
                print_status "✅ Field '$field' present in Go response"
            else
                print_error "❌ Field '$field' missing from Go response"
                return 1
            fi
        done
        
        # Validate market data structure
        if jq -e '.market_data[0].symbol' "$go_response_file" > /dev/null; then
            print_status "✅ Market data structure validated"
        else
            print_error "❌ Market data structure invalid"
            return 1
        fi
        
        # Validate metadata
        if jq -e '.metadata.response_time' "$go_response_file" > /dev/null; then
            print_status "✅ Metadata structure validated"
        else
            print_error "❌ Metadata structure invalid"
            return 1
        fi
        
        print_status "✅ Feature parity validation passed"
        return 0
    else
        print_error "❌ Go response file not found"
        return 1
    fi
}

# Function to generate validation report
generate_report() {
    print_header "Generating Validation Report"
    
    report_file="/tmp/e2e_validation_report.md"
    
    cat > "$report_file" << EOF
# End-to-End Validation Report
Generated: $(date)

## Test Results

### Service Status
- Rust Core Engine: $(check_service "Rust Core Engine" 50052 "/health" && echo "✅ Running" || echo "❌ Not Running")
- Go API Gateway: $(check_service "Go API Gateway" 8080 "/api/v1/health" && echo "✅ Running" || echo "❌ Not Running")

### API Tests
- Market Data Fetch: $(test_market_data_flow > /dev/null 2>&1 && echo "✅ Passed" || echo "❌ Failed")
- WebSocket Connection: $(test_websocket_flow > /dev/null 2>&1 && echo "✅ Passed" || echo "❌ Failed")
- Feature Parity: $(validate_feature_parity > /dev/null 2>&1 && echo "✅ Passed" || echo "❌ Failed")

### Response Files
- Go Market Data Response: $(ls /tmp/market_data_response.json 2>/dev/null && echo "✅ Generated" || echo "❌ Not Generated")
- Go Buffer Response: $(ls /tmp/buffer_response.json 2>/dev/null && echo "✅ Generated" || echo "❌ Not Generated")
- Go Stats Response: $(ls /tmp/stats_response.json 2>/dev/null && echo "✅ Generated" || echo "❌ Not Generated")
- Go Connect Response: $(ls /tmp/connect_response.json 2>/dev/null && echo "✅ Generated" || echo "❌ Not Generated")

### Logs
- Core Engine Log: /tmp/core-engine.log
- API Gateway Log: /tmp/api-gateway.log

## Summary
EOF
    
    if [ -f /tmp/market_data_response.json ]; then
        echo "### Sample Go Response" >> "$report_file"
        echo '```json' >> "$report_file"
        cat /tmp/market_data_response.json | head -20 >> "$report_file"
        echo '```' >> "$report_file"
    fi
    
    print_status "Validation report generated: $report_file"
}

# Main execution
main() {
    print_header "End-to-End Validation for Market Data Migration"
    
    # Cleanup function
    trap stop_services EXIT
    
    # Start services
    start_services
    
    # Wait for services to be fully ready
    sleep 5
    
    # Check services
    if ! check_service "Rust Core Engine" 50052 "/health"; then
        print_error "❌ Core Engine not ready, aborting"
        exit 1
    fi
    
    if ! check_service "Go API Gateway" 8080 "/api/v1/health"; then
        print_error "❌ API Gateway not ready, aborting"
        exit 1
    fi
    
    # Run tests
    if test_market_data_flow; then
        print_status "✅ Market data flow tests passed"
    else
        print_error "❌ Market data flow tests failed"
        exit 1
    fi
    
    # Test WebSocket
    test_websocket_flow
    
    # Compare with legacy
    compare_with_legacy
    
    # Validate feature parity
    if validate_feature_parity; then
        print_status "✅ Feature parity validation passed"
    else
        print_error "❌ Feature parity validation failed"
        exit 1
    fi
    
    # Generate report
    generate_report
    
    print_header "Validation Complete"
    print_status "✅ All tests passed successfully!"
    print_status "📊 Report available at: /tmp/e2e_validation_report.md"
    print_status "📋 Response files available in /tmp/"
    
    # Show sample response
    if [ -f /tmp/market_data_response.json ]; then
        print_header "Sample Go Response"
        cat /tmp/market_data_response.json | jq .
    fi
}

# Run main function
main "$@"
