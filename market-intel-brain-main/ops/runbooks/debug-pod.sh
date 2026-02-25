#!/bin/bash

# Debug Pod Script for Market Intel Brain
# Launches ephemeral debug container attached to production pod with net-tools

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

# Debug container configuration
DEBUG_IMAGE="nicolaka/netshoot"
DEBUG_IMAGE_TAG="latest"
DEBUG_CONTAINER_NAME="debug-$(date +%s)"
DEBUG_TTL="3600"  # 1 hour

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
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check if debug feature is available
    if ! kubectl debug --help &> /dev/null; then
        print_error "kubectl debug command is not available. Please upgrade to kubectl 1.18+"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# List available pods
list_pods() {
    print_header "Available Pods in Namespace: $NAMESPACE"
    
    # Get all pods with their status
    kubectl get pods -n $NAMESPACE -o wide --show-labels
    
    echo ""
    echo "Pod types:"
    echo "  api-gateway: Go API Gateway service"
    echo "  core-engine: Rust Core Engine service"
    echo "  postgres: PostgreSQL database"
    echo "  redis: Redis cache"
    echo "  prometheus: Prometheus monitoring"
    echo "  grafana: Grafana dashboard"
    echo "  jaeger: Jaeger tracing"
}

# Validate target pod
validate_target_pod() {
    local target_pod=$1
    
    if [[ -z "$target_pod" ]]; then
        print_error "Target pod name is required"
        return 1
    fi
    
    # Check if pod exists
    if ! kubectl get pod $target_pod -n $NAMESPACE &> /dev/null; then
        print_error "Pod $target_pod not found in namespace $NAMESPACE"
        return 1
    fi
    
    # Check pod status
    local pod_status=$(kubectl get pod $target_pod -n $NAMESPACE -o jsonpath='{.status.phase}')
    if [[ "$pod_status" != "Running" ]]; then
        print_warning "Pod $target_pod is not running (status: $pod_status)"
        print_status "Debugging may be limited"
    fi
    
    # Get pod IP
    local pod_ip=$(kubectl get pod $target_pod -n $NAMESPACE -o jsonpath='{.status.podIP}')
    if [[ -n "$pod_ip" ]]; then
        print_status "Target pod IP: $pod_ip"
    fi
    
    return 0
}

# Create debug pod
create_debug_pod() {
    local target_pod=$1
    local debug_image=${2:-$DEBUG_IMAGE}
    local debug_tag=${3:-$DEBUG_IMAGE_TAG}
    
    print_header "Creating Debug Pod"
    
    # Get target pod node
    local target_node=$(kubectl get pod $target_pod -n $NAMESPACE -o jsonpath='{.spec.nodeName}')
    print_status "Target pod $target_pod is running on node: $target_node"
    
    # Create debug pod
    print_status "Creating debug pod: $DEBUG_CONTAINER_NAME"
    
    cat > /tmp/debug-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: $DEBUG_CONTAINER_NAME
  namespace: $NAMESPACE
  labels:
    app: debug-pod
    debug-target: $target_pod
spec:
  nodeName: $target_node
  restartPolicy: Never
  terminationGracePeriodSeconds: 30
  containers:
  - name: debug-container
    image: $debug_image:$debug_tag
    command: ["/bin/bash"]
    args: ["-c", "sleep $DEBUG_TTL"]
    securityContext:
      privileged: true
      capabilities:
        add: ["NET_ADMIN", "NET_RAW"]
    volumeMounts:
    - name: proc
      mountPath: /host/proc
      readOnly: true
    - name: sys
      mountPath: /host/sys
      readOnly: true
    - name: root
      mountPath: /host/root
      readOnly: true
    env:
    - name: TARGET_POD
      value: $target_pod
    - name: TARGET_POD_IP
      value: $(kubectl get pod $target_pod -n $NAMESPACE -o jsonpath='{.status.podIP}')
  volumes:
  - name: proc
    hostPath:
      path: /proc
  - name: sys
    hostPath:
      path: /sys
  - name: root
    hostPath:
      path: /root
  tolerations:
  - key: node.kubernetes.io/not-ready
    operator: Exists
    effect: NoSchedule
  - key: node.kubernetes.io/unreachable
    operator: Exists
    effect: NoSchedule
  nodeSelector:
    kubernetes.io/hostname: $target_node
EOF
    
    # Apply debug pod
    kubectl apply -f /tmp/debug-pod.yaml
    
    # Wait for debug pod to be ready
    print_status "Waiting for debug pod to be ready..."
    local max_wait=60
    local wait_time=0
    
    while [[ $wait_time -lt $max_wait ]]; do
        local pod_status=$(kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE -o jsonpath='{.status.phase}' 2>/dev/null)
        local pod_ready=$(kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)
        
        if [[ "$pod_status" == "Running" && "$pod_ready" == "True" ]]; then
            print_status "Debug pod is ready"
            break
        fi
        
        sleep 2
        wait_time=$((wait_time + 2))
        print_status "Waiting for debug pod... (${wait_time}s/${max_wait}s)"
    done
    
    if [[ $wait_time -ge $max_wait ]]; then
        print_error "Debug pod failed to become ready within $max_wait seconds"
        kubectl delete pod $DEBUG_CONTAINER_NAME -n $NAMESPACE --ignore-not-found=true
        return 1
    fi
    
    # Clean up temp file
    rm -f /tmp/debug-pod.yaml
    
    return 0
}

# Show debug pod information
show_debug_info() {
    local target_pod=$1
    
    print_header "Debug Pod Information"
    
    echo "Target Pod: $target_pod"
    echo "Debug Pod: $DEBUG_CONTAINER_NAME"
    echo "Namespace: $NAMESPACE"
    echo "TTL: $DEBUG_TTL seconds"
    echo ""
    
    # Show debug pod status
    kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE -o wide
    
    echo ""
    echo "Debug Pod Environment:"
    kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- env | grep -E "(TARGET_POD|TARGET_POD_IP)"
    
    echo ""
    echo "Available Debug Commands:"
    echo "  kubectl exec -it $DEBUG_CONTAINER_NAME -n $NAMESPACE -- bash"
    echo "  kubectl attach $DEBUG_CONTAINER_NAME -n $NAMESPACE -c debug-container"
    echo "  kubectl logs $DEBUG_CONTAINER_NAME -n $NAMESPACE"
    echo ""
    echo "Network Debug Commands (from debug pod):"
    echo "  ping \$TARGET_POD_IP"
    echo "  traceroute \$TARGET_POD_IP"
    echo "  netstat -an"
    echo "  ss -tulpn"
    echo "  tcpdump -i any"
    echo ""
    echo "System Debug Commands (from debug pod):"
    echo "  cat /host/proc/\$TARGET_POD_IP/status"
    echo "  ls -la /host/proc/\$TARGET_POD_IP"
    echo "  cat /host/sys/fs/cgroup/memory/\$TARGET_POD_IP/memory.usage_in_bytes"
    echo ""
    echo "Cleanup Commands:"
    echo "  kubectl delete pod $DEBUG_CONTAINER_NAME -n $NAMESPACE"
    echo "  kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- exit"
}

# Execute debug commands
execute_debug_commands() {
    local target_pod=$1
    local command_type=$2
    
    print_header "Executing Debug Commands: $command_type"
    
    case "$command_type" in
        "network")
            print_status "Running network diagnostics..."
            
            # Get target pod IP
            local target_ip=$(kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- printenv TARGET_POD_IP)
            
            echo "Target Pod IP: $target_ip"
            echo ""
            
            # Ping test
            print_status "Ping test:"
            kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- ping -c 3 $target_ip || true
            
            echo ""
            # Traceroute
            print_status "Traceroute:"
            kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- traceroute $target_ip || true
            
            echo ""
            # Network connections
            print_status "Network connections:"
            kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- netstat -an | grep ":$target_ip" || true
            ;;
            
        "system")
            print_status "Running system diagnostics..."
            
            # Get target pod PID
            local target_pid=$(kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- cat /host/proc/*/status | grep -B5 "Name: $target_pod" | grep "Pid:" | head -1 | awk '{print $2}')
            
            echo "Target Pod PID: $target_pid"
            echo ""
            
            # Process information
            if [[ -n "$target_pid" ]]; then
                print_status "Process status:"
                kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- cat /host/proc/$target_pid/status || true
                
                echo ""
                print_status "Process limits:"
                kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- cat /host/proc/$target_pid/limits || true
                
                echo ""
                print_status "Process memory usage:"
                kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- cat /host/proc/$target_pid/status | grep -E "(VmRSS|VmSize|RSS)" || true
            fi
            ;;
            
        "logs")
            print_status "Collecting logs from target pod..."
            kubectl logs $target_pod -n $NAMESPACE --tail=50 || true
            ;;
            
        "events")
            print_status "Recent events for target pod:"
            kubectl get events -n $NAMESPACE --field-selector involvedObject.name=$target_pod --sort-by='.lastTimestamp' || true
            ;;
            
        "describe")
            print_status "Pod description:"
            kubectl describe pod $target_pod -n $NAMESPACE || true
            ;;
            
        *)
            print_error "Unknown command type: $command_type"
            echo "Available types: network, system, logs, events, describe"
            return 1
            ;;
    esac
}

# Interactive debug session
interactive_debug() {
    local target_pod=$1
    
    print_header "Starting Interactive Debug Session"
    
    print_status "Entering debug pod shell..."
    print_status "Target pod: $target_pod"
    print_status "Debug pod: $DEBUG_CONTAINER_NAME"
    print_status "Type 'exit' to leave the debug session"
    echo ""
    
    # Show available debug commands
    echo "Quick commands:"
    echo "  ping \$TARGET_POD_IP                    # Ping target pod"
    echo "  cat /host/proc/\$(cat /host/proc/*/status | grep -B5 'Name: $target_pod' | grep 'Pid:' | head -1 | awk '{print \$2}')/status  # Target pod process status"
    echo "  kubectl logs $target_pod -n $NAMESPACE  # Target pod logs"
    echo "  kubectl describe pod $target_pod -n $NAMESPACE  # Target pod description"
    echo ""
    
    # Enter debug pod
    kubectl exec -it $DEBUG_CONTAINER_NAME -n $NAMESPACE -- bash || true
}

# Cleanup debug pod
cleanup_debug_pod() {
    print_header "Cleaning Up Debug Pod"
    
    if kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE &> /dev/null; then
        print_status "Deleting debug pod: $DEBUG_CONTAINER_NAME"
        kubectl delete pod $DEBUG_CONTAINER_NAME -n $NAMESPACE --ignore-not-found=true
        print_status "Debug pod deleted"
    else
        print_status "Debug pod not found"
    fi
}

# Generate debug report
generate_debug_report() {
    local target_pod=$1
    local report_dir="$PROJECT_ROOT/reports/debug/$(date +%Y%m%d_%H%M%S)"
    
    print_status "Generating debug report: $report_dir"
    
    mkdir -p "$report_dir"
    
    cat > "$report_dir/debug-report.md" << EOF
# Debug Pod Report

## Target Pod: $target_pod
## Debug Pod: $DEBUG_CONTAINER_NAME
## Namespace: $NAMESPACE
## Debug Date: $(date)

## Target Pod Information
\`\`\`
$(kubectl get pod $target_pod -n $NAMESPACE -o yaml)
\`\`\`

## Debug Pod Information
\`\`\`
$(kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE -o yaml)
\`\`\`

## Network Diagnostics
\`\`\`
$(kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- ping -c 3 \$TARGET_POD_IP 2>/dev/null || echo "Ping failed")
\`\`\`

## System Diagnostics
\`\`\`
$(kubectl exec $DEBUG_CONTAINER_NAME -n $NAMESPACE -- cat /host/proc/*/status | grep -A10 -B5 "Name: $target_pod" 2>/dev/null || echo "Process info not found")
\`\`\`

## Events
\`\`\`
$(kubectl get events -n $NAMESPACE --field-selector involvedObject.name=$target_pod --sort-by='.lastTimestamp' 2>/dev/null || echo "No events found")
\`\`\`

## Logs
\`\`\`
$(kubectl logs $target_pod -n $NAMESPACE --tail=50 2>/dev/null || echo "No logs available")
\`\`\`

## Cleanup Commands
\`\`\`bash
# Delete debug pod
kubectl delete pod $DEBUG_CONTAINER_NAME -n $NAMESPACE

# Check if debug pod is gone
kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE
\`\`\`
EOF
    
    print_status "Debug report generated: $report_dir/debug-report.md"
}

# Main execution
main() {
    case "${1:-help}" in
        "create")
            if [[ -z "$2" ]]; then
                print_error "Target pod name is required"
                echo "Usage: $0 create <pod-name> [image] [tag]"
                echo ""
                echo "Available pods:"
                list_pods
                exit 1
            fi
            
            check_prerequisites
            validate_target_pod "$2"
            create_debug_pod "$2" "${3:-$DEBUG_IMAGE}" "${4:-$DEBUG_IMAGE_TAG}"
            show_debug_info "$2"
            ;;
        "interactive")
            if [[ -z "$2" ]]; then
                print_error "Target pod name is required"
                echo "Usage: $0 interactive <pod-name>"
                exit 1
            fi
            
            if ! kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE &> /dev/null; then
                print_error "Debug pod not found. Create it first with: $0 create <pod-name>"
                exit 1
            fi
            
            interactive_debug "$2"
            ;;
        "exec")
            if [[ -z "$2" ]]; then
                print_error "Target pod name is required"
                echo "Usage: $0 exec <pod-name> <command-type>"
                echo "Available command types: network, system, logs, events, describe"
                exit 1
            fi
            
            if ! kubectl get pod $DEBUG_CONTAINER_NAME -n $NAMESPACE &> /dev/null; then
                print_error "Debug pod not found. Create it first with: $0 create <pod-name>"
                exit 1
            fi
            
            execute_debug_commands "$2" "$3"
            ;;
        "cleanup")
            cleanup_debug_pod
            ;;
        "report")
            if [[ -z "$2" ]]; then
                print_error "Target pod name is required"
                echo "Usage: $0 report <pod-name>"
                exit 1
            fi
            
            generate_debug_report "$2"
            ;;
        "list")
            list_pods
            ;;
        "help"|"-h"|"--help")
            echo "Market Intel Brain Debug Pod Script"
            echo ""
            echo "Usage: $0 {create|interactive|exec|cleanup|report|list|help}"
            echo ""
            echo "Commands:"
            echo "  create <pod> [image] [tag]  - Create debug pod attached to target pod"
            echo "  interactive <pod>            - Start interactive debug session"
            echo "  exec <pod> <command>        - Execute debug commands"
            echo "  cleanup                      - Clean up debug pod"
            echo "  report <pod>                - Generate debug report"
            echo "  list                         - List available pods"
            echo "  help                         - Show this help message"
            echo ""
            echo "Debug command types:"
            echo "  network    - Network diagnostics (ping, traceroute, netstat)"
            echo "  system     - System diagnostics (process info, memory usage)"
            echo "  logs       - Collect logs from target pod"
            echo "  events     - Show recent events for target pod"
            echo "  describe   - Show pod description"
            echo ""
            echo "Environment variables:"
            echo "  DEBUG_IMAGE=custom/image    - Use custom debug image"
            echo "  DEBUG_TTL=7200               - Debug pod TTL in seconds"
            echo ""
            echo "Examples:"
            echo "  $0 create api-gateway-12345"
            echo "  $0 create core-engine-67890 nicolaka/netshoot latest"
            echo "  $0 interactive api-gateway-12345"
            echo "  $0 exec api-gateway-12345 network"
            echo "  $0 exec core-engine-67890 system"
            echo "  $0 cleanup"
            echo "  $0 report api-gateway-12345"
            echo "  $0 list"
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
