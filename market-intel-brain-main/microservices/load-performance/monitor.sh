#!/bin/bash

# Performance Monitoring Script for Market Intel Brain
# Monitors system resources and service performance during load testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_GATEWAY_URL="http://localhost:8080"
CORE_ENGINE_URL="http://localhost:50052"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"
JAEGER_URL="http://localhost:16686"
MONITORING_INTERVAL=5  # seconds
RESULTS_DIR="performance-results"

# Create results directory
mkdir -p "$RESULTS_DIR"

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

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local url=$2
    
    if curl -f -s "$url" > /dev/null; then
        print_status "$service_name is healthy"
        return 0
    else
        print_error "$service_name is not healthy"
        return 1
    fi
}

# Function to get system metrics
get_system_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    
    # Memory usage
    local memory_info=$(free -m | awk 'NR==2{printf "%.2f", $3*100/$2}')
    
    # Disk usage
    local disk_usage=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)
    
    # Network connections
    local connections=$(netstat -an | grep ESTABLISHED | wc -l)
    
    echo "$timestamp,$cpu_usage,$memory_info,$disk_usage,$connections"
}

# Function to get API Gateway metrics
get_api_gateway_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Health check response time
    local health_time=$(curl -o /dev/null -s -w '%{time_total}' "$API_GATEWAY_URL/api/v1/health")
    
    # Get metrics from Prometheus endpoint
    local metrics_response=$(curl -s "$API_GATEWAY_URL/api/v1/metrics" 2>/dev/null || echo "")
    
    # Extract key metrics
    local requests_total=$(echo "$metrics_response" | grep "requests_total" | tail -1 | awk '{print $2}' || echo "0")
    local error_rate=$(echo "$metrics_response" | grep "errors_total" | tail -1 | awk '{print $2}' || echo "0")
    
    echo "$timestamp,$health_time,$requests_total,$error_rate"
}

# Function to get Core Engine metrics
get_core_engine_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Check if Core Engine is responding
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' "$CORE_ENGINE_URL" || echo "0")
    
    echo "$timestamp,$response_time"
}

# Function to get Prometheus metrics
get_prometheus_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Get total requests
    local total_requests=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=sum(http_requests_total)" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    # Get error rate
    local error_rate=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=sum(http_errors_total)/sum(http_requests_total)" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    # Get average response time
    local avg_response_time=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=avg(http_request_duration_seconds)" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    echo "$timestamp,$total_requests,$error_rate,$avg_response_time"
}

# Function to monitor services during load test
monitor_services() {
    local duration=$1
    local end_time=$(($(date +%s) + duration))
    
    print_header "Starting Performance Monitoring"
    print_status "Monitoring for $duration seconds..."
    print_status "Results will be saved to $RESULTS_DIR/"
    
    # Create CSV files for metrics
    local system_metrics_file="$RESULTS_DIR/system_metrics.csv"
    local api_metrics_file="$RESULTS_DIR/api_gateway_metrics.csv"
    local core_metrics_file="$RESULTS_DIR/core_engine_metrics.csv"
    local prometheus_metrics_file="$RESULTS_DIR/prometheus_metrics.csv"
    
    # Write CSV headers
    echo "timestamp,cpu_usage,memory_usage,disk_usage,connections" > "$system_metrics_file"
    echo "timestamp,health_time,requests_total,error_rate" > "$api_metrics_file"
    echo "timestamp,response_time" > "$core_metrics_file"
    echo "timestamp,total_requests,error_rate,avg_response_time" > "$prometheus_metrics_file"
    
    # Monitor loop
    while [ $(date +%s) -lt $end_time ]; do
        echo "Collecting metrics at $(date '+%Y-%m-%d %H:%M:%S')"
        
        # Get metrics
        get_system_metrics >> "$system_metrics_file"
        get_api_gateway_metrics >> "$api_metrics_file"
        get_core_engine_metrics >> "$core_metrics_file"
        get_prometheus_metrics >> "$prometheus_metrics_file"
        
        # Check service health
        if ! check_service_health "API Gateway" "$API_GATEWAY_URL/api/v1/health"; then
            print_error "API Gateway health check failed!"
        fi
        
        if ! check_service_health "Core Engine" "$CORE_ENGINE_URL"; then
            print_error "Core Engine health check failed!"
        fi
        
        sleep "$MONITORING_INTERVAL"
    done
    
    print_status "Monitoring completed!"
}

# Function to generate performance report
generate_report() {
    local report_file="$RESULTS_DIR/performance_report.md"
    
    print_header "Generating Performance Report"
    
    cat > "$report_file" << EOF
# Performance Report

Generated: $(date)

## System Metrics

### CPU Usage
\`\`\`
$(tail -10 "$RESULTS_DIR/system_metrics.csv" | column -t -s ',')
\`\`\`

### Memory Usage
\`\`\`
$(tail -10 "$RESULTS_DIR/system_metrics.csv" | column -t -s ',')
\`\`\`

### API Gateway Metrics

### Response Times
\`\`\`
$(tail -10 "$RESULTS_DIR/api_gateway_metrics.csv" | column -t -s ',')
\`\`\`

### Request Rates
\`\`\`
$(tail -10 "$RESULTS_DIR/prometheus_metrics.csv" | column -t -s ',')
\`\`\`

## Performance Analysis

### Key Metrics
- Average Response Time: $(awk -F',' '{sum+=$3} END {print sum/NR}' "$RESULTS_DIR/api_gateway_metrics.csv")s
- Total Requests: $(tail -1 "$RESULTS_DIR/prometheus_metrics.csv" | cut -d',' -f2)
- Error Rate: $(tail -1 "$RESULTS_DIR/prometheus_metrics.csv" | cut -d',' -f3)%

### Recommendations
- Monitor CPU usage during peak load
- Check memory allocation patterns
- Analyze response time trends
- Review error rates and patterns

## Files Generated
- \`system_metrics.csv\` - System resource usage
- \`api_gateway_metrics.csv\` - API Gateway performance
- \`core_engine_metrics.csv\` - Core Engine performance
- \`prometheus_metrics.csv\` - Prometheus metrics
EOF
    
    print_status "Performance report generated: $report_file"
}

# Function to create real-time dashboard
create_dashboard() {
    print_header "Starting Real-time Dashboard"
    
    # Create a simple HTML dashboard
    local dashboard_file="$RESULTS_DIR/dashboard.html"
    
    cat > "$dashboard_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Market Intel Brain Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .chart-container { margin: 20px 0; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .metric { background: #f5f5f5; padding: 15px; border-radius: 5px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #333; }
        .metric-label { color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Market Intel Brain Performance Dashboard</h1>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value" id="cpu-usage">0%</div>
                <div class="metric-label">CPU Usage</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="memory-usage">0%</div>
                <div class="metric-label">Memory Usage</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="response-time">0ms</div>
                <div class="metric-label">Response Time</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="request-rate">0/s</div>
                <div class="metric-label">Request Rate</div>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="responseTimeChart"></canvas>
        </div>
        
        <div class="chart-container">
            <canvas id="requestRateChart"></canvas>
        </div>
    </div>
    
    <script>
        // Initialize charts
        const responseTimeCtx = document.getElementById('responseTimeChart').getContext('2d');
        const requestRateCtx = document.getElementById('requestRateChart').getContext('2d');
        
        const responseTimeChart = new Chart(responseTimeCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Response Time (ms)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        const requestRateChart = new Chart(requestRateCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Request Rate (/s)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // Update metrics (this would normally fetch from an API)
        function updateMetrics() {
            // Simulated data - replace with actual API calls
            document.getElementById('cpu-usage').textContent = Math.random() * 100 + '%';
            document.getElementById('memory-usage').textContent = Math.random() * 100 + '%';
            document.getElementById('response-time').textContent = Math.floor(Math.random() * 100) + 'ms';
            document.getElementById('request-rate').textContent = Math.floor(Math.random() * 1000) + '/s';
        }
        
        // Update metrics every 5 seconds
        setInterval(updateMetrics, 5000);
        updateMetrics();
    </script>
</body>
</html>
EOF
    
    print_status "Dashboard created: $dashboard_file"
    print_status "Open in browser: file://$(pwd)/$dashboard_file"
}

# Main execution
main() {
    case "${1:-monitor}" in
        "monitor")
            monitor_services "${2:-300}"  # Default 5 minutes
            generate_report
            ;;
        "report")
            generate_report
            ;;
        "dashboard")
            create_dashboard
            ;;
        "health")
            print_header "Service Health Check"
            check_service_health "API Gateway" "$API_GATEWAY_URL/api/v1/health"
            check_service_health "Core Engine" "$CORE_ENGINE_URL"
            check_service_health "Prometheus" "$PROMETHEUS_URL/-/healthy"
            check_service_health "Grafana" "$GRAFANA_URL/api/health"
            check_service_health "Jaeger" "$JAEGER_URL/"
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 {monitor|report|dashboard|health} [duration]"
            echo ""
            echo "Commands:"
            echo "  monitor [duration]  - Monitor services for specified duration (default: 300s)"
            echo "  report              - Generate performance report"
            echo "  dashboard           - Create real-time dashboard"
            echo "  health              - Check service health"
            echo ""
            echo "Examples:"
            echo "  $0 monitor 600      # Monitor for 10 minutes"
            echo "  $0 report           # Generate report from existing data"
            echo "  $0 dashboard        # Create HTML dashboard"
            echo "  $0 health           # Check all service health"
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
