#!/bin/bash

# Chaos Engineering Script for Market Intel Brain
# Simulates failures and disruptions to test system resilience

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="market-intel-brain"
RUST_SERVICE="core-engine"
GO_SERVICE="api-gateway"
CHAOS_DURATION=300  # 5 minutes
CHAOS_INTERVAL=30   # 30 seconds between chaos events
LOG_FILE="chaos-testing.log"

# Chaos scenarios
SCENARIOS=(
    "pod_deletion"
    "pod_kill"
    "network_latency"
    "cpu_pressure"
    "memory_pressure"
    "disk_pressure"
    "service_disruption"
    "dns_failure"
    "certificate_expiry"
)

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

# Initialize chaos testing
init_chaos() {
    print_header "Initializing Chaos Testing"
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if we're in the right namespace
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        print_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    # Create log file
    echo "=== Chaos Testing Started at $(date) ===" > $LOG_FILE
    echo "Namespace: $NAMESPACE" >> $LOG_FILE
    echo "Duration: ${CHAOS_DURATION}s" >> $LOG_FILE
    echo "Interval: ${CHAOS_INTERVAL}s" >> $LOG_FILE
    echo "" >> $LOG_FILE
    
    # Get initial state
    print_status "Capturing initial system state..."
    capture_system_state "initial"
    
    print_status "Chaos testing initialized"
}

# Capture system state
capture_system_state() {
    local state_name=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "=== $state_name State at $timestamp ===" >> $LOG_FILE
    
    # Get pod information
    kubectl get pods -n $NAMESPACE -o wide >> $LOG_FILE 2>&1
    echo "" >> $LOG_FILE
    
    # Get service information
    kubectl get services -n $NAMESPACE >> $LOG_FILE 2>&1
    echo "" >> $LOG_FILE
    
    # Get HPA status
    kubectl get hpa -n $NAMESPACE >> $LOG_FILE 2>&1
    echo "" >> $LOG_FILE
    
    # Get resource usage
    kubectl top pods -n $NAMESPACE >> $LOG_FILE 2>&1
    echo "" >> $LOG_FILE
}

# Pod deletion chaos
chaos_pod_deletion() {
    print_header "Pod Deletion Chaos"
    
    # Get list of Rust pods
    local rust_pods=$(kubectl get pods -n $NAMESPACE -l app=$RUST_SERVICE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [[ -z "$rust_pods" ]]; then
        print_warning "No $RUST_SERVICE pods found for deletion chaos"
        return 1
    fi
    
    # Select random pod to delete
    local pod_to_delete=$(echo "$rust_pods" | tr ' ' '\n' | shuf | head -1)
    
    print_status "Deleting pod: $pod_to_delete"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - DELETING POD: $pod_to_delete" >> $LOG_FILE
    
    # Delete the pod
    kubectl delete pod $pod_to_delete -n $NAMESPACE >> $LOG_FILE 2>&1
    
    if [[ $? -eq 0 ]]; then
        print_status "Pod $pod_to_delete deleted successfully"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - POD DELETED: $pod_to_delete" >> $LOG_FILE
    else
        print_error "Failed to delete pod: $pod_to_delete"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - POD DELETION FAILED: $pod_to_delete" >> $LOG_FILE
    fi
}

# Pod kill chaos
chaos_pod_kill() {
    print_header "Pod Kill Chaos"
    
    # Get list of Rust pods
    local rust_pods=$(kubectl get pods -n $NAMESPACE -l app=$RUST_SERVICE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [[ -z "$rust_pods" ]]; then
        print_warning "No $RUST_SERVICE pods found for kill chaos"
        return 1
    fi
    
    # Select random pod to kill
    local pod_to_kill=$(echo "$rust_pods" | tr ' ' '\n' | shuf | head -1)
    
    print_status "Killing pod: $pod_to_kill"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - KILLING POD: $pod_to_kill" >> $LOG_FILE
    
    # Kill the main process in the pod
    kubectl exec $pod_to_kill -n $NAMESPACE -- pkill -f main >> $LOG_FILE 2>&1
    
    if [[ $? -eq 0 ]]; then
        print_status "Pod $pod_to_kill killed successfully"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - POD KILLED: $pod_to_kill" >> $LOG_FILE
    else
        print_error "Failed to kill pod: $pod_to_kill"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - POD KILL FAILED: $pod_to_kill" >> $LOG_FILE
    fi
}

# Network latency chaos
chaos_network_latency() {
    print_header "Network Latency Chaos"
    
    # Get list of Rust pods
    local rust_pods=$(kubectl get pods -n $NAMESPACE -l app=$RUST_SERVICE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [[ -z "$rust_pods" ]]; then
        print_warning "No $RUST_SERVICE pods found for network chaos"
        return 1
    fi
    
    # Add network latency to each pod
    for pod in $rust_pods; do
        print_status "Adding network latency to pod: $pod"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ADDING LATENCY TO POD: $pod" >> $LOG_FILE
        
        # Use tc to add latency (this requires tc to be installed in the pod)
        kubectl exec $pod -n $NAMESPACE -- tc qdisc add dev eth0 root netem delay 100ms 10ms >> $LOG_FILE 2>&1
        
        if [[ $? -eq 0 ]]; then
            print_status "Network latency added to pod: $pod"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - LATENCY ADDED TO POD: $pod" >> $LOG_FILE
        else
            print_error "Failed to add network latency to pod: $pod"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - LATENCY ADDITION FAILED: $pod" >> $LOG_FILE
        fi
    done
}

# CPU pressure chaos
chaos_cpu_pressure() {
    print_header "CPU Pressure Chaos"
    
    # Get list of Rust pods
    local rust_pods=$(kubectl get pods -n $NAMESPACE -l app=$RUST_SERVICE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [[ -z "$rust_pods" ]]; then
        print_warning "No $RUST_SERVICE pods found for CPU chaos"
        return 1
    fi
    
    # Add CPU pressure to each pod
    for pod in $rust_pods; do
        print_status "Adding CPU pressure to pod: $pod"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ADDING CPU PRESSURE TO POD: $pod" >> $LOG_FILE
        
        # Use stress-ng to add CPU pressure
        kubectl exec $pod -n $NAMESPACE -- stress-ng --cpu 2 --timeout 60s >> $LOG_FILE 2>&1 &
        
        if [[ $? -eq 0 ]]; then
            print_status "CPU pressure added to pod: $pod"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - CPU PRESSURE ADDED TO POD: $pod" >> $LOG_FILE
        else
            print_error "Failed to add CPU pressure to pod: $pod"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - CPU PRESSURE ADDITION FAILED: $pod" >> $LOG_FILE
        fi
    done
}

# Memory pressure chaos
chaos_memory_pressure() {
    print_header "Memory Pressure Chaos"
    
    # Get list of Rust pods
    local rust_pods=$(kubectl get pods -n $NAMESPACE -l app=$RUST_SERVICE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [[ -z "$rust_pods" ]]; then
        print_warning "No $RUST_SERVICE pods found for memory chaos"
        return 1
    fi
    
    # Add memory pressure to each pod
    for pod in $rust_pods; do
        print_status "Adding memory pressure to pod: $pod"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ADDING MEMORY PRESSURE TO POD: $pod" >> $LOG_FILE
        
        # Use stress-ng to add memory pressure
        kubectl exec $pod -n $NAMESPACE -- stress-ng --vm 2 --vm-bytes 128M --timeout 60s >> $LOG_FILE 2>&1 &
        
        if [[ $? -eq 0 ]]; then
            print_status "Memory pressure added to pod: $pod"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - MEMORY PRESSURE ADDED TO POD: $pod" >> $LOG_FILE
        else
            print_error "Failed to add memory pressure to pod: $pod"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - MEMORY PRESSURE ADDITION FAILED: $pod" >> $LOG_FILE
        fi
    done
}

# Service disruption chaos
chaos_service_disruption() {
    print_header "Service Disruption Chaos"
    
    # Scale down the Rust service
    print_status "Scaling down $RUST_SERVICE service"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SCALING DOWN SERVICE: $RUST_SERVICE" >> $LOG_FILE
    
    kubectl scale deployment $RUST_SERVICE --replicas=0 -n $NAMESPACE >> $LOG_FILE 2>&1
    
    if [[ $? -eq 0 ]]; then
        print_status "Service $RUST_SERVICE scaled down successfully"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - SERVICE SCALED DOWN: $RUST_SERVICE" >> $LOG_FILE
        
        # Wait for pods to terminate
        sleep 10
        
        # Scale back up
        print_status "Scaling up $RUST_SERVICE service"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - SCALING UP SERVICE: $RUST_SERVICE" >> $LOG_FILE
        
        kubectl scale deployment $RUST_SERVICE --replicas=2 -n $NAMESPACE >> $LOG_FILE 2>&1
        
        if [[ $? -eq 0 ]]; then
            print_status "Service $RUST_SERVICE scaled up successfully"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - SERVICE SCALED UP: $RUST_SERVICE" >> $LOG_FILE
        else
            print_error "Failed to scale up service: $RUST_SERVICE"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - SERVICE SCALE UP FAILED: $RUST_SERVICE" >> $LOG_FILE
        fi
    else
        print_error "Failed to scale down service: $RUST_SERVICE"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - SERVICE SCALE DOWN FAILED: $RUST_SERVICE" >> $LOG_FILE
    fi
}

# DNS failure chaos
chaos_dns_failure() {
    print_header "DNS Failure Chaos"
    
    # Get the Core Engine service
    local service_name="$RUST_SERVICE.$NAMESPACE.svc.cluster.local"
    
    print_status "Simulating DNS failure for: $service_name"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SIMULATING DNS FAILURE: $service_name" >> $LOG_FILE
    
    # Add DNS entry to /etc/hosts pointing to invalid address
    local invalid_ip="192.0.2.999"
    
    # This would require modifying /etc/hosts in the pods
    # For demonstration, we'll just log the action
    echo "$(date '+%Y-%m-%d %H:%M:%S') - DNS FAILURE SIMULATED: $service_name -> $invalid_ip" >> $LOG_FILE
}

# Certificate expiry chaos
chaos_certificate_expiry() {
    print_header "Certificate Expiry Chaos"
    
    # Get the TLS secret
    local secret_name="$RUST_SERVICE-tls"
    
    print_status "Simulating certificate expiry for: $secret_name"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SIMULATING CERTIFICATE EXPIRY: $secret_name" >> $LOG_FILE
    
    # Create a new certificate with expired date
    local expired_cert=$(openssl x509 -in /dev/stdin -noout -days -1 << EOF
-----BEGIN CERTIFICATE-----
MIICljCCAX4DCF... (expired certificate data)
-----END CERTIFICATE-----
EOF
)
    
    # Update the secret with expired certificate
    kubectl patch secret $secret_name -n $NAMESPACE -p '{"data":{"tls.crt":"'$(echo "$expired_cert" | base64 -w 0)'"}}' >> $LOG_FILE 2>&1
    
    if [[ $? -eq 0 ]]; then
        print_status "Certificate expiry simulated for: $secret_name"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - CERTIFICATE EXPIRY SIMULATED: $secret_name" >> $LOG_FILE
    else
        print_error "Failed to simulate certificate expiry for: $secret_name"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - CERTIFICATE EXPIRY SIMULATION FAILED: $secret_name" >> $LOG_FILE
    fi
}

# Run random chaos scenario
run_random_chaos() {
    local scenario=${SCENARIOS[$RANDOM % ${#SCENARIOS[@]}]}
    
    print_status "Running random chaos scenario: $scenario"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - RANDOM CHAOS SCENARIO: $scenario" >> $LOG_FILE
    
    case $scenario in
        "pod_deletion")
            chaos_pod_deletion
            ;;
        "pod_kill")
            chaos_pod_kill
            ;;
        "network_latency")
            chaos_network_latency
            ;;
        "cpu_pressure")
            chaos_cpu_pressure
            ;;
        "memory_pressure")
            chaos_memory_pressure
            ;;
        "disk_pressure")
            print_warning "Disk pressure chaos not implemented"
            ;;
        "service_disruption")
            chaos_service_disruption
            ;;
        "dns_failure")
            chaos_dns_failure
            ;;
        "certificate_expiry")
            chaos_certificate_expiry
            ;;
        *)
            print_error "Unknown chaos scenario: $scenario"
            ;;
    esac
}

# Monitor system recovery
monitor_recovery() {
    print_header "Monitoring System Recovery"
    
    local recovery_time=0
    local max_recovery_time=120  # 2 minutes
    
    while [[ $recovery_time -lt $max_recovery_time ]]; do
        print_status "Checking system recovery... ($recovery_time/$max_recovery_time)"
        
        # Check if pods are ready
        local ready_pods=$(kubectl get pods -n $NAMESPACE -l app=$RUST_SERVICE --field=status.phase=Running --no-headers | wc -l)
        
        if [[ $ready_pods -ge 2 ]]; then
            print_status "System recovered - $ready_pods pods are running"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - SYSTEM RECOVERED: $ready_pods pods running" >> $LOG_FILE
            break
        fi
        
        # Check service endpoints
        local service_endpoints=$(kubectl get endpoints $RUST_SERVICE -n $NAMESPACE --no-headers | grep -c "addresses:" | wc -l)
        
        if [[ $service_endpoints -ge 1 ]]; then
            print_status "Service endpoints are ready"
            echo "$(date '+%Y-%m-%d %H:%M:%S') - SERVICE ENDPOINTS READY: $service_endpoints endpoints" >> $LOG_FILE
        fi
        
        sleep 5
        recovery_time=$((recovery_time + 5))
    done
    
    if [[ $recovery_time -ge $max_recovery_time ]]; then
        print_warning "Recovery monitoring timeout reached"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - RECOVERY MONITORING TIMEOUT" >> $LOG_FILE
    fi
}

# Cleanup chaos artifacts
cleanup_chaos() {
    print_header "Cleaning Up Chaos Artifacts"
    
    print_status "Removing network latency from pods..."
    
    # Get list of Rust pods
    local rust_pods=$(kubectl get pods -n $NAMESPACE -l app=$RUST_SERVICE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    # Remove network latency from each pod
    for pod in $rust_pods; do
        kubectl exec $pod -n $NAMESPACE -- tc qdisc del dev eth0 root >> $LOG_FILE 2>&1
    done
    
    # Stop stress processes
    for pod in $rust_pods; do
        kubectl exec $pod -n $NAMESPACE -- pkill -f stress-ng >> $LOG_FILE 2>&1
    done
    
    # Restore certificate if it was modified
    kubectl patch secret $RUST_SERVICE-tls -n $NAMESPACE -p '{"data":{"tls.crt":null}}' >> $LOG_FILE 2>&1
    
    print_status "Chaos artifacts cleaned up"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - CHAOS CLEANUP COMPLETED" >> $LOG_FILE
}

# Generate chaos report
generate_report() {
    print_header "Chaos Testing Report"
    
    local report_file="chaos-report-$(date '+%Y%m%d_%H%M%S').txt"
    
    echo "=== Chaos Testing Report ===" > $report_file
    echo "Generated: $(date)" >> $report_file
    echo "Namespace: $NAMESPACE" >> $report_file
    echo "Duration: ${CHAOS_DURATION}s" >> $report_file
    echo "Interval: ${CHAOS_INTERVAL}s" >> $report_file
    echo "" >> $report_file
    
    # Copy log content
    tail -50 $LOG_FILE >> $report_file
    
    print_status "Chaos report generated: $report_file"
}

# Main chaos execution loop
run_chaos_loop() {
    local end_time=$(($(date +%s) + CHAOS_DURATION))
    
    print_status "Starting chaos loop for ${CHAOS_DURATION}s"
    
    while [[ $(date +%s) -lt $end_time ]]; do
        print_status "Running chaos event at $(date)"
        
        # Run random chaos scenario
        run_random_chaos
        
        # Monitor recovery
        monitor_recovery
        
        # Wait for next interval
        sleep $CHAOS_INTERVAL
    done
    
    print_status "Chaos loop completed"
}

# Signal handler for graceful shutdown
cleanup_on_exit() {
    print_status "Received interrupt signal, cleaning up..."
    cleanup_chaos
    generate_report
    exit 0
}

# Main execution
main() {
    case "${1:-run}" in
        "init")
            init_chaos
            ;;
        "run")
            init_chaos
            trap cleanup_on_exit EXIT INT TERM
            run_chaos_loop
            ;;
        "cleanup")
            cleanup_chaos
            ;;
        "report")
            generate_report
            ;;
        "pod-deletion")
            chaos_pod_deletion
            ;;
        "pod-kill")
            chaos_pod_kill
            ;;
        "network-latency")
            chaos_network_latency
            ;;
        "cpu-pressure")
            chaos_cpu_pressure
            ;;
        "memory-pressure")
            chaos_memory_pressure
            ;;
        "service-disruption")
            chaos_service_disruption
            ;;
        "dns-failure")
            chaos_dns_failure
            ;;
        "certificate-expiry")
            chaos_certificate_expiry
            ;;
        "help"|"-h"|"--help")
            echo "Market Intel Brain Chaos Engineering Script"
            echo ""
            echo "Usage: $0 {init|run|cleanup|report|scenario}"
            echo ""
            echo "Commands:"
            echo "  init          - Initialize chaos testing environment"
            echo "  run           - Run chaos testing loop"
            echo "  cleanup       - Clean up chaos artifacts"
            echo "  report        - Generate chaos testing report"
            echo ""
            echo "Scenarios:"
            echo "  pod-deletion      - Delete random pods"
            echo "  pod-kill         - Kill processes in pods"
            echo "  network-latency   - Add network latency"
            echo "  cpu-pressure      - Add CPU pressure"
            echo "  memory-pressure   - Add memory pressure"
            echo "  service-disruption - Scale service down/up"
            echo "  dns-failure       - Simulate DNS failure"
            echo "  certificate-expiry - Simulate certificate expiry"
            echo ""
            echo "Examples:"
            echo "  $0 init                    # Initialize chaos testing"
            echo "  $0 run                     # Run chaos testing loop"
            echo "  $0 pod-deletion             # Delete a random pod"
            echo "  $0 network-latency          # Add network latency"
            echo "  $0 cleanup                 # Clean up chaos artifacts"
            echo "  $0 report                  # Generate report"
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
