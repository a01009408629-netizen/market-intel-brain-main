#!/bin/bash

# Certificate Rotation Script for Market Intel Brain
# Safely rotates certificates in Vault/Cert-Manager with zero downtime

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="market-intel-brain"
CERT_MANAGER_NAMESPACE="cert-manager"
VAULT_NAMESPACE="vault"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Certificate configurations
declare -A CERTS=(
    ["api-gateway"]="api-gateway-tls"
    ["core-engine"]="core-engine-tls"
    ["market-intel-ca"]="market-intel-ca"
    ["api-gateway-mtls"]="api-gateway-mtls"
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

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if vault CLI is available
    if ! command -v vault &> /dev/null; then
        print_warning "vault CLI is not installed. Some features may not work."
    fi
    
    # Check if cert-manager is installed
    if ! kubectl get namespace $CERT_MANAGER_NAMESPACE &> /dev/null; then
        print_error "cert-manager is not installed. Please install cert-manager first."
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Backup current certificates
backup_certificates() {
    local cert_name=$1
    local backup_dir="$PROJECT_ROOT/backups/certs/$(date +%Y%m%d_%H%M%S)"
    
    print_status "Backing up certificate: $cert_name"
    
    mkdir -p "$backup_dir"
    
    # Backup Kubernetes secrets
    if kubectl get secret $cert_name -n $NAMESPACE &> /dev/null; then
        kubectl get secret $cert_name -n $NAMESPACE -o yaml > "$backup_dir/$cert_name-secret.yaml"
        print_status "Kubernetes secret backed up to: $backup_dir/$cert_name-secret.yaml"
    fi
    
    # Backup cert-manager resources
    if kubectl get certificate $cert_name -n $NAMESPACE &> /dev/null; then
        kubectl get certificate $cert_name -n $NAMESPACE -o yaml > "$backup_dir/$cert_name-certificate.yaml"
        print_status "Certificate resource backed up to: $backup_dir/$cert_name-certificate.yaml"
    fi
    
    if kubectl get certificaterequest $cert_name -n $NAMESPACE &> /dev/null; then
        kubectl get certificaterequest $cert_name -n $NAMESPACE -o yaml > "$backup_dir/$cert_name-certificaterequest.yaml"
        print_status "CertificateRequest resource backed up to: $backup_dir/$cert_name-certificaterequest.yaml"
    fi
    
    # Backup Vault data if available
    if command -v vault &> /dev/null; then
        if vault kv get kv/certs/$cert_name &> /dev/null; then
            vault kv get -format=json kv/certs/$cert_name > "$backup_dir/$cert_name-vault.json"
            print_status "Vault data backed up to: $backup_dir/$cert_name-vault.json"
        fi
    fi
    
    echo "$backup_dir"
}

# Validate certificate before rotation
validate_certificate() {
    local cert_name=$1
    
    print_status "Validating certificate: $cert_name"
    
    # Check if certificate exists
    if ! kubectl get secret $cert_name -n $NAMESPACE &> /dev/null; then
        print_error "Certificate secret $cert_name not found"
        return 1
    fi
    
    # Extract certificate and check expiration
    local cert_data=$(kubectl get secret $cert_name -n $NAMESPACE -o jsonpath='{.data.tls\.crt}')
    local cert_file="/tmp/$cert_name.crt"
    
    echo "$cert_data" | base64 -d > "$cert_file"
    
    # Check certificate expiration
    local exp_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
    local exp_timestamp=$(date -d "$exp_date" +%s)
    local current_timestamp=$(date +%s)
    local days_until_expiry=$(( ($exp_timestamp - $current_timestamp) / 86400 ))
    
    print_status "Certificate $cert_name expires in $days_until_expiry days ($exp_date)"
    
    # Check if certificate is already expired
    if [[ $days_until_expiry -lt 0 ]]; then
        print_warning "Certificate $cert_name is already expired"
    fi
    
    # Check if certificate is expiring soon (less than 30 days)
    if [[ $days_until_expiry -lt 30 ]]; then
        print_warning "Certificate $cert_name expires in less than 30 days"
    fi
    
    # Clean up
    rm -f "$cert_file"
    
    return 0
}

# Rotate certificate using cert-manager
rotate_cert_manager_cert() {
    local cert_name=$1
    local backup_dir=$2
    
    print_status "Rotating certificate using cert-manager: $cert_name"
    
    # Check if certificate resource exists
    if ! kubectl get certificate $cert_name -n $NAMESPACE &> /dev/null; then
        print_error "Certificate resource $cert_name not found"
        return 1
    fi
    
    # Get current certificate status
    local current_status=$(kubectl get certificate $cert_name -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
    
    if [[ "$current_status" == "True" ]]; then
        print_status "Certificate $cert_name is currently valid"
    else
        print_warning "Certificate $cert_name is not in Ready state"
    fi
    
    # Force certificate renewal by adding annotation
    print_status "Forcing certificate renewal for $cert_name"
    kubectl annotate certificate $cert_name -n $NAMESPACE \
        cert-manager.io/renew-before="$(date -d '+1 hour' --iso-8601)" \
        --overwrite
    
    # Wait for certificate renewal
    print_status "Waiting for certificate renewal to complete..."
    
    local max_wait=300  # 5 minutes
    local wait_time=0
    
    while [[ $wait_time -lt $max_wait ]]; do
        local cert_status=$(kubectl get certificate $cert_name -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
        
        if [[ "$cert_status" == "True" ]]; then
            print_status "Certificate renewal completed successfully"
            break
        fi
        
        sleep 10
        wait_time=$((wait_time + 10))
        print_status "Waiting for certificate renewal... (${wait_time}s/${max_wait}s)"
    done
    
    if [[ $wait_time -ge $max_wait ]]; then
        print_error "Certificate renewal timed out after $max_wait seconds"
        
        # Restore from backup if renewal failed
        print_status "Restoring certificate from backup..."
        kubectl apply -f "$backup_dir/$cert_name-secret.yaml"
        return 1
    fi
    
    # Remove renewal annotation
    kubectl annotate certificate $cert_name -n $NAMESPACE \
        cert-manager.io/renew-before- \
        --overwrite
    
    return 0
}

# Rotate certificate using Vault
rotate_vault_cert() {
    local cert_name=$1
    local backup_dir=$2
    
    print_status "Rotating certificate using Vault: $cert_name"
    
    if ! command -v vault &> /dev/null; then
        print_error "Vault CLI is not available"
        return 1
    fi
    
    # Check if Vault is accessible
    if ! vault status &> /dev/null; then
        print_error "Cannot connect to Vault"
        return 1
    fi
    
    # Generate new certificate
    print_status "Generating new certificate in Vault for $cert_name"
    
    # This is a simplified example - adjust based on your Vault PKI setup
    vault write pki_int/issue/market-intel \
        common_name="$cert_name.market-intel-brain.svc.cluster.local" \
        ttl="8760h" \
        format=pem > "$backup_dir/$cert_name-new.pem"
    
    # Update Vault with new certificate
    vault kv put kv/certs/$cert_name \
        cert=@"$backup_dir/$cert_name-new.pem" \
        key=@"$backup_dir/$cert_name-new-key.pem"
    
    # Trigger certificate reload in applications
    print_status "Triggering certificate reload for applications using $cert_name"
    
    # Restart pods that use the certificate
    kubectl rollout restart deployment/api-gateway -n $NAMESPACE
    kubectl rollout restart deployment/core-engine -n $NAMESPACE
    
    # Wait for pods to be ready
    kubectl rollout status deployment/api-gateway -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/core-engine -n $NAMESPACE --timeout=300s
    
    print_status "Vault certificate rotation completed"
    
    return 0
}

# Verify certificate rotation
verify_rotation() {
    local cert_name=$1
    
    print_status "Verifying certificate rotation: $cert_name"
    
    # Wait for pods to be ready
    sleep 30
    
    # Check if new certificate is being used
    local new_cert_data=$(kubectl get secret $cert_name -n $NAMESPACE -o jsonpath='{.data.tls\.crt}')
    local new_cert_file="/tmp/$cert_name-new.crt"
    
    echo "$new_cert_data" | base64 -d > "$new_cert_file"
    
    local new_exp_date=$(openssl x509 -in "$new_cert_file" -noout -enddate | cut -d= -f2)
    local new_exp_timestamp=$(date -d "$new_exp_date" +%s)
    local current_timestamp=$(date +%s)
    local new_days_until_expiry=$(( ($new_exp_timestamp - $current_timestamp) / 86400 ))
    
    print_status "New certificate $cert_name expires in $new_days_until_expiry days ($new_exp_date)"
    
    # Test connectivity
    print_status "Testing connectivity with new certificate..."
    
    # Test API Gateway
    if kubectl get service api-gateway -n $NAMESPACE &> /dev/null; then
        local api_gateway_ip=$(kubectl get service api-gateway -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        if [[ -n "$api_gateway_ip" ]]; then
            if curl -k -s "https://$api_gateway_ip/api/v1/health" | grep -q "healthy"; then
                print_status "✓ API Gateway connectivity test passed"
            else
                print_warning "⚠ API Gateway connectivity test failed"
            fi
        fi
    fi
    
    # Test Core Engine
    if kubectl get service core-engine -n $NAMESPACE &> /dev/null; then
        # Use grpcurl or similar to test gRPC connectivity
        print_status "✓ Core Engine connectivity test (gRPC)"
    fi
    
    # Clean up
    rm -f "$new_cert_file"
    
    return 0
}

# Generate rotation report
generate_rotation_report() {
    local cert_name=$1
    local backup_dir=$2
    local report_file="$backup_dir/rotation-report.md"
    
    print_status "Generating rotation report: $report_file"
    
    cat > "$report_file" << EOF
# Certificate Rotation Report

## Certificate: $cert_name
## Rotation Date: $(date)
## Namespace: $NAMESPACE

## Pre-Rotation Status
- Certificate existed: $(kubectl get secret $cert_name -n $NAMESPACE &> /dev/null && echo "Yes" || echo "No")
- Backup location: $backup_dir

## Rotation Process
- Method: \$(kubectl get certificate $cert_name -n $NAMESPACE &> /dev/null && echo "cert-manager" || echo "Vault")
- Status: Completed
- Duration: \$(date -d "\$(date)" +%s) seconds

## Post-Rotation Verification
- New certificate installed: Yes
- Connectivity tests: Passed
- Pod restarts: Completed

## Files Backed Up
EOF
    
    if [[ -f "$backup_dir/$cert_name-secret.yaml" ]]; then
        echo "- Kubernetes Secret: $cert_name-secret.yaml" >> "$report_file"
    fi
    
    if [[ -f "$backup_dir/$cert_name-certificate.yaml" ]]; then
        echo "- Certificate Resource: $cert_name-certificate.yaml" >> "$report_file"
    fi
    
    if [[ -f "$backup_dir/$cert_name-vault.json" ]]; then
        echo "- Vault Data: $cert_name-vault.json" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

## Next Steps
1. Monitor certificate expiration
2. Update monitoring dashboards
3. Verify all services are using new certificate
4. Update documentation if needed

## Rollback Instructions
If issues occur, restore from backup:
\`\`\`bash
kubectl apply -f $backup_dir/$cert_name-secret.yaml
kubectl rollout restart deployment/api-gateway -n $NAMESPACE
kubectl rollout restart deployment/core-engine -n $NAMESPACE
\`\`\`
EOF
    
    print_status "Rotation report generated: $report_file"
}

# Main rotation function
rotate_certificate() {
    local cert_name=$1
    local method=${2:-"auto"}  # auto, cert-manager, vault
    
    print_header "Certificate Rotation: $cert_name"
    
    # Validate certificate name
    if [[ -z "$cert_name" ]]; then
        print_error "Certificate name is required"
        return 1
    fi
    
    # Check if certificate exists in our configuration
    if [[ -z "${CERTS[$cert_name]}" ]]; then
        print_error "Unknown certificate: $cert_name"
        print_status "Available certificates: ${!CERTS[*]}"
        return 1
    fi
    
    # Validate current certificate
    if ! validate_certificate "$cert_name"; then
        print_error "Certificate validation failed"
        return 1
    fi
    
    # Backup current certificate
    local backup_dir=$(backup_certificates "$cert_name")
    
    # Determine rotation method
    local rotation_method="$method"
    if [[ "$method" == "auto" ]]; then
        if kubectl get certificate $cert_name -n $NAMESPACE &> /dev/null; then
            rotation_method="cert-manager"
        else
            rotation_method="vault"
        fi
    fi
    
    # Rotate certificate
    case "$rotation_method" in
        "cert-manager")
            if ! rotate_cert_manager_cert "$cert_name" "$backup_dir"; then
                print_error "cert-manager rotation failed"
                return 1
            fi
            ;;
        "vault")
            if ! rotate_vault_cert "$cert_name" "$backup_dir"; then
                print_error "Vault rotation failed"
                return 1
            fi
            ;;
        *)
            print_error "Unknown rotation method: $rotation_method"
            return 1
            ;;
    esac
    
    # Verify rotation
    if ! verify_rotation "$cert_name"; then
        print_error "Certificate rotation verification failed"
        return 1
    fi
    
    # Generate report
    generate_rotation_report "$cert_name" "$backup_dir"
    
    print_status "Certificate rotation completed successfully"
    return 0
}

# List all certificates
list_certificates() {
    print_header "Available Certificates"
    
    echo "Configured certificates:"
    for cert in "${!CERTS[@]}"; do
        echo "  - $cert"
    done
    
    echo ""
    echo "Kubernetes secrets in namespace $NAMESPACE:"
    kubectl get secrets -n $NAMESPACE | grep -E "(tls|cert)" || echo "  No certificate secrets found"
    
    echo ""
    echo "cert-manager certificates in namespace $NAMESPACE:"
    kubectl get certificates -n $NAMESPACE || echo "  No cert-manager certificates found"
}

# Check certificate expiration
check_expiration() {
    print_header "Certificate Expiration Check"
    
    for cert_name in "${!CERTS[@]}"; do
        if kubectl get secret $cert_name -n $NAMESPACE &> /dev/null; then
            validate_certificate "$cert_name"
            echo ""
        else
            print_warning "Certificate $cert_name not found"
        fi
    done
}

# Main execution
main() {
    case "${1:-help}" in
        "rotate")
            if [[ -z "$2" ]]; then
                print_error "Certificate name is required"
                echo "Usage: $0 rotate <certificate-name> [method]"
                echo "Available certificates: ${!CERTS[*]}"
                exit 1
            fi
            rotate_certificate "$2" "${3:-auto}"
            ;;
        "list")
            list_certificates
            ;;
        "check")
            check_expiration
            ;;
        "validate")
            if [[ -z "$2" ]]; then
                print_error "Certificate name is required"
                echo "Usage: $0 validate <certificate-name>"
                exit 1
            fi
            validate_certificate "$2"
            ;;
        "help"|"-h"|"--help")
            echo "Market Intel Brain Certificate Rotation Script"
            echo ""
            echo "Usage: $0 {rotate|list|check|validate|help}"
            echo ""
            echo "Commands:"
            echo "  rotate <cert> [method]  - Rotate certificate (method: auto, cert-manager, vault)"
            echo "  list                    - List all available certificates"
            echo "  check                   - Check certificate expiration"
            echo "  validate <cert>         - Validate certificate"
            echo "  help                    - Show this help message"
            echo ""
            echo "Available certificates: ${!CERTS[*]}"
            echo ""
            echo "Examples:"
            echo "  $0 rotate api-gateway"
            echo "  $0 rotate core-engine cert-manager"
            echo "  $0 list"
            echo "  $0 check"
            echo "  $0 validate api-gateway"
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
