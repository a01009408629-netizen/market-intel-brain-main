#!/bin/bash

# Development Pre-start Script for Market Intel Brain
# Sets up the development environment before starting services

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

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if kubernetes cluster is accessible
    if ! kubectl cluster-info > /dev/null 2>&1; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Create namespace if it doesn't exist
create_namespace() {
    print_header "Creating Namespace"
    
    if ! kubectl get namespace $NAMESPACE > /dev/null 2>&1; then
        print_status "Creating namespace: $NAMESPACE"
        kubectl create namespace $NAMESPACE
    else
        print_status "Namespace $NAMESPACE already exists"
    fi
}

# Set up development certificates
setup_dev_certificates() {
    print_header "Setting up Development Certificates"
    
    # Generate development certificates
    if [[ ! -f "$PROJECT_ROOT/security/certs/dev-certs.sh" ]]; then
        print_error "Development certificate script not found at $PROJECT_ROOT/security/certs/dev-certs.sh"
        return 1
    fi
    
    cd "$PROJECT_ROOT/security/certs"
    ./generate-certs.sh
    cd "$PROJECT_ROOT"
    
    # Apply development certificates
    if kubectl get secret market-intel-dev-certs -n $NAMESPACE > /dev/null 2>&1; then
        print_status "Updating existing development certificates"
        kubectl delete secret market-intel-dev-certs -n $NAMESPACE
    fi
    
    # Create development certificates secret
    kubectl create secret generic market-intel-dev-certs \
        --from-file=client-cert=certs/client.crt \
        --from-file=client-key=certs/client.key \
        --from-file=ca-cert=certs/ca.crt \
        --namespace=$NAMESPACE
    
    print_status "Development certificates set up"
}

# Set up database for development
setup_dev_database() {
    print_header "Setting up Development Database"
    
    # Check if PostgreSQL is running
    if ! kubectl get pods -n $NAMESPACE -l app=postgres > /dev/null 2>&1; then
        print_status "Starting PostgreSQL for development"
        kubectl apply -f "$PROJECT_ROOT/deploy/k8s/dev/postgres.yaml"
        
        # Wait for PostgreSQL to be ready
        print_status "Waiting for PostgreSQL to be ready..."
        kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    else
        print_status "PostgreSQL is already running"
    fi
}

# Set up Redis for development
setup_dev_redis() {
    print_header "Setting up Development Redis"
    
    # Check if Redis is running
    if ! kubectl get pods -n $NAMESPACE -l app=redis > /dev/null 2>&1; then
        print_status "Starting Redis for development"
        kubectl apply -f "$PROJECT_ROOT/deploy/k8s/dev/redis.yaml"
        
        # Wait for Redis to be ready
        print_status "Waiting for Redis to be ready..."
        kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s
    else
        print_status "Redis is already running"
    fi
}

# Set up observability stack for development
setup_dev_observability() {
    print_header "Setting up Development Observability Stack"
    
    # Check if observability components are running
    local observability_running=$(kubectl get pods -n $NAMESPACE -l app in (prometheus,grafana,jaeger) --no-headers | wc -l)
    
    if [[ $observability_running -lt 3 ]]; then
        print_status "Starting observability stack for development"
        kubectl apply -f "$PROJECT_ROOT/deploy/k8s/dev/observability.yaml"
        
        # Wait for observability components to be ready
        print_status "Waiting for observability stack to be ready..."
        kubectl wait --for=condition=ready pod -l app in (prometheus,grafana,jaeger) -n $NAMESPACE --timeout=300s
    else
        print_status "Observability stack is already running"
    fi
}

# Set up port forwarding
setup_port_forwarding() {
    print_header "Setting up Port Forwarding"
    
    # Kill existing port forwarding processes
    print_status "Cleaning up existing port forwarding..."
    pkill -f "kubectl port-forward" || true
    
    # Set up port forwarding in background
    print_status "Setting up port forwarding..."
    
    # API Gateway port forwarding
    kubectl port-forward deployment/api-gateway 8080:8080 -n $NAMESPACE &
    PF_PID1=$!
    
    # Core Engine port forwarding
    kubectl port-forward deployment/core-engine 50052:50052 -n $NAMESPACE &
    PF_PID2=$!
    
    # PostgreSQL port forwarding
    kubectl port-forward postgres 5432:5432 -n $NAMESPACE &
    PF_PID3=$!
    
    # Redis port forwarding
    kubectl port-forward redis 6379:6379 -n $NAMESPACE &
    PF_PID4=$!
    
    # Prometheus port forwarding
    kubectl port-forward prometheus 9090:9090 -n $NAMESPACE &
    PF_PID5=$!
    
    # Grafana port forwarding
    kubectl port-forward grafana 3000:3000 -n $NAMESPACE &
    PF_PID6=$!
    
    # Jaeger port forwarding
    kubectl port-forward jaeger 16686:16686 -n $NAMESPACE &
    PF_PID7=$!
    
    # Jaeger collector port forwarding
    kubectl port-forward jaeger 14268:14268 -n $NAMESPACE &
    PF_PID8=$!
    
    # Save PIDs for cleanup
    echo "$PF_PID1 $PF_PID2 $PF_PID3 $PF_PID4 $PF_PID5 $PF_PID6 $PF_PID7 $PF_PID8" > "$PROJECT_ROOT/.port_forward_pids"
    
    print_status "Port forwarding set up"
    print_status "API Gateway: http://localhost:8080"
    print_status "Core Engine: grpc://localhost:50052"
    print_status "PostgreSQL: localhost:5432"
    print_status "Redis: localhost:6379"
    print_status "Prometheus: http://localhost:9090"
    print_status "Grafana: http://localhost:3000"
    print_status "Jaeger: http://localhost:16686"
}

# Run database migrations
run_database_migrations() {
    print_header "Running Database Migrations"
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    
    # Run migrations
    print_status "Running database migrations..."
    kubectl exec deployment/api-gateway -n $NAMESPACE -- \
        ./bin/api-gateway migrate --config /etc/config/config.yaml
    
    if [[ $? -eq 0 ]]; then
        print_status "Database migrations completed successfully"
    else
        print_error "Database migrations failed"
    fi
}

# Set up development environment variables
setup_dev_environment() {
    print_header "Setting up Development Environment"
    
    # Create development config map
    kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: dev-env-config
  namespace: $NAMESPACE
data:
  ENVIRONMENT: "development"
  DEBUG: "true"
  LOG_LEVEL: "debug"
  SKIP_TLS_VERIFY: "true"
  DATABASE_URL: "postgresql://postgres:postgres@localhost:5432/market_intel_dev"
  REDIS_URL: "redis://localhost:6379/0"
  CORE_ENGINE_URL: "core-engine:50052"
  JAEGER_ENDPOINT: "http://localhost:14268/api/traces"
  PROMETHEUS_ENDPOINT: "http://localhost:9090"
EOF
    
    print_status "Development environment variables set up"
}

# Display development information
show_dev_info() {
    print_header "Development Environment Information"
    
    echo "Namespace: $NAMESPACE"
    echo "API Gateway: http://localhost:8080"
    echo "Core Engine: grpc://localhost:50052"
    echo "PostgreSQL: localhost:5432"
    echo "Redis: localhost:6379"
    echo "Prometheus: http://localhost:9090"
    echo "Grafana: http://localhost:3000"
    echo "Jaeger: http://localhost:16686"
    echo ""
    echo "Useful commands:"
    echo "  kubectl logs -f deployment/api-gateway -n $NAMESPACE"
    echo "  kubectl logs -f deployment/core-engine -n $NAMESPACE"
    echo "  kubectl exec -it deployment/api-gateway -n $NAMESPACE -- /bin/sh"
    echo "  tilt up"
    echo "  skaffold dev"
    echo ""
    echo "To stop port forwarding: pkill -f 'kubectl port-forward'"
}

# Main execution
main() {
    case "${1:-setup}" in
        "setup")
            check_prerequisites
            create_namespace
            setup_dev_certificates
            setup_dev_database
            setup_dev_redis
            setup_dev_observability
            setup_port_forwarding
            setup_dev_environment
            show_dev_info
            ;;
        "cleanup")
            print_header "Cleaning up Development Environment"
            
            # Kill port forwarding
            if [[ -f "$PROJECT_ROOT/.port_forward_pids" ]]; then
                while read -r pid; do
                    kill $pid 2>/dev/null
                done < "$PROJECT_ROOT/.port_forward_pids"
                rm "$PROJECT_ROOT/.port_forward_pids"
            fi
            
            # Delete development resources
            kubectl delete namespace $NAMESPACE --ignore-not-found=true
            
            print_status "Development environment cleaned up"
            ;;
        "migrate")
            check_prerequisites
            run_database_migrations
            ;;
        "info")
            show_dev_info
            ;;
        "help"|"-h"|"--help")
            echo "Market Intel Brain Development Pre-start Script"
            echo ""
            echo "Usage: $0 {setup|cleanup|migrate|info}"
            echo ""
            echo "Commands:"
            echo "  setup    - Set up complete development environment"
            echo "  cleanup  - Clean up development environment"
            echo "  migrate  - Run database migrations"
            echo "  info     - Show development environment information"
            echo ""
            echo "Examples:"
            echo "  $0 setup"
            echo "  $0 cleanup"
            echo "  $0 migrate"
            echo "  $0 info"
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
