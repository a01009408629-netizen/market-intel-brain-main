#!/bin/bash

# Certificate Generation Script for Market Intel Brain mTLS
# Generates Root CA, Server Certs, and Client Certs for secure gRPC communication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDITY_DAYS=3650  # 10 years
COUNTRY="US"
STATE="California"
LOCALITY="San Francisco"
ORGANIZATION="Market Intel Brain"
ORGANIZATIONAL_UNIT="Engineering"
COMMON_NAME="market-intel-brain"
EMAIL="security@market-intel.com"

# Service configurations
RUST_SERVICE="core-engine"
GO_SERVICE="api-gateway"
RUST_SERVICE_DNS="core-engine.market-intel-brain.svc.cluster.local"
GO_SERVICE_DNS="api-gateway.market-intel-brain.svc.cluster.local"
RUST_SERVICE_IP="10.0.0.10"
GO_SERVICE_IP="10.0.0.11"

# Create directories
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

# Create directory structure
create_directories() {
    print_header "Creating Directory Structure"
    
    mkdir -p "$CERT_DIR/ca"
    mkdir -p "$CERT_DIR/server"
    mkdir -p "$CERT_DIR/client"
    mkdir -p "$CERT_DIR/k8s-secrets"
    mkdir -p "$CERT_DIR/vault"
    
    print_status "Directory structure created"
}

# Generate Root CA
generate_root_ca() {
    print_header "Generating Root Certificate Authority"
    
    # CA private key
    openssl genrsa -out "$CERT_DIR/ca/ca-key.pem" 4096
    
    # CA certificate
    openssl req -new -x509 -days $VALIDITY_DAYS -key "$CERT_DIR/ca/ca-key.pem" \
        -out "$CERT_DIR/ca/ca-cert.pem" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$COMMON_NAME/emailAddress=$EMAIL"
    
    # CA serial file
    echo "1000" > "$CERT_DIR/ca/serial"
    
    # CA database
    touch "$CERT_DIR/ca/index.txt"
    
    print_status "Root CA generated successfully"
    print_status "CA Certificate: $CERT_DIR/ca/ca-cert.pem"
    print_status "CA Private Key: $CERT_DIR/ca/ca-key.pem"
}

# Generate Server Certificate for Rust Service
generate_server_cert() {
    print_header "Generating Server Certificate for Rust Service ($RUST_SERVICE)"
    
    # Server private key
    openssl genrsa -out "$CERT_DIR/server/$RUST_SERVICE-key.pem" 2048
    
    # Server CSR
    openssl req -new -key "$CERT_DIR/server/$RUST_SERVICE-key.pem" \
        -out "$CERT_DIR/server/$RUST_SERVICE.csr" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$RUST_SERVICE_DNS/emailAddress=$EMAIL"
    
    # Create server extension file
    cat > "$CERT_DIR/server/$RUST_SERVICE-ext.cnf" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $RUST_SERVICE_DNS
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = $RUST_SERVICE_IP
EOF
    
    # Sign server certificate with CA
    openssl x509 -req -in "$CERT_DIR/server/$RUST_SERVICE.csr" \
        -CA "$CERT_DIR/ca/ca-cert.pem" -CAkey "$CERT_DIR/ca/ca-key.pem" \
        -CAcreateserial -out "$CERT_DIR/server/$RUST_SERVICE-cert.pem" \
        -days $VALIDITY_DAYS -extensions v3_req -extfile "$CERT_DIR/server/$RUST_SERVICE-ext.cnf"
    
    # Verify server certificate
    openssl verify -CAfile "$CERT_DIR/ca/ca-cert.pem" "$CERT_DIR/server/$RUST_SERVICE-cert.pem"
    
    print_status "Server certificate generated for $RUST_SERVICE"
    print_status "Server Certificate: $CERT_DIR/server/$RUST_SERVICE-cert.pem"
    print_status "Server Private Key: $CERT_DIR/server/$RUST_SERVICE-key.pem"
}

# Generate Client Certificate for Go Service
generate_client_cert() {
    print_header "Generating Client Certificate for Go Service ($GO_SERVICE)"
    
    # Client private key
    openssl genrsa -out "$CERT_DIR/client/$GO_SERVICE-key.pem" 2048
    
    # Client CSR
    openssl req -new -key "$CERT_DIR/client/$GO_SERVICE-key.pem" \
        -out "$CERT_DIR/client/$GO_SERVICE.csr" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$GO_SERVICE/emailAddress=$EMAIL"
    
    # Create client extension file
    cat > "$CERT_DIR/client/$GO_SERVICE-ext.cnf" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = clientAuth
EOF
    
    # Sign client certificate with CA
    openssl x509 -req -in "$CERT_DIR/client/$GO_SERVICE.csr" \
        -CA "$CERT_DIR/ca/ca-cert.pem" -CAkey "$CERT_DIR/ca/ca-key.pem" \
        -CAcreateserial -out "$CERT_DIR/client/$GO_SERVICE-cert.pem" \
        -days $VALIDITY_DAYS -extensions v3_req -extfile "$CERT_DIR/client/$GO_SERVICE-ext.cnf"
    
    # Verify client certificate
    openssl verify -CAfile "$CERT_DIR/ca/ca-cert.pem" "$CERT_DIR/client/$GO_SERVICE-cert.pem"
    
    print_status "Client certificate generated for $GO_SERVICE"
    print_status "Client Certificate: $CERT_DIR/client/$GO_SERVICE-cert.pem"
    print_status "Client Private Key: $CERT_DIR/client/$GO_SERVICE-key.pem"
}

# Generate PKCS12 format for easier distribution
generate_pkcs12() {
    print_header "Generating PKCS12 Format Certificates"
    
    # Server PKCS12
    openssl pkcs12 -export -out "$CERT_DIR/server/$RUST_SERVICE.p12" \
        -inkey "$CERT_DIR/server/$RUST_SERVICE-key.pem" \
        -in "$CERT_DIR/server/$RUST_SERVICE-cert.pem" \
        -certfile "$CERT_DIR/ca/ca-cert.pem" \
        -passout pass:$RUST_SERVICE
    
    # Client PKCS12
    openssl pkcs12 -export -out "$CERT_DIR/client/$GO_SERVICE.p12" \
        -inkey "$CERT_DIR/client/$GO_SERVICE-key.pem" \
        -in "$CERT_DIR/client/$GO_SERVICE-cert.pem" \
        -certfile "$CERT_DIR/ca/ca-cert.pem" \
        -passout pass:$GO_SERVICE
    
    print_status "PKCS12 certificates generated"
}

# Generate Kubernetes Secrets
generate_k8s_secrets() {
    print_header "Generating Kubernetes Secrets"
    
    # CA secret
    kubectl create secret generic market-intel-ca \
        --from-file=ca-cert="$CERT_DIR/ca/ca-cert.pem" \
        --from-file=ca-key="$CERT_DIR/ca/ca-key.pem" \
        --namespace=market-intel-brain \
        --dry-run=client -o yaml > "$CERT_DIR/k8s-secrets/ca-secret.yaml"
    
    # Server secret (Rust service)
    kubectl create secret generic $RUST_SERVICE-tls \
        --from-file=tls-cert="$CERT_DIR/server/$RUST_SERVICE-cert.pem" \
        --from-file=tls-key="$CERT_DIR/server/$RUST_SERVICE-key.pem" \
        --from-file=ca-cert="$CERT_DIR/ca/ca-cert.pem" \
        --namespace=market-intel-brain \
        --dry-run=client -o yaml > "$CERT_DIR/k8s-secrets/$RUST_SERVICE-tls-secret.yaml"
    
    # Client secret (Go service)
    kubectl create secret generic $GO_SERVICE-mtls \
        --from-file=client-cert="$CERT_DIR/client/$GO_SERVICE-cert.pem" \
        --from-file=client-key="$CERT_DIR/client/$GO_SERVICE-key.pem" \
        --from-file=ca-cert="$CERT_DIR/ca/ca-cert.pem" \
        --namespace=market-intel-brain \
        --dry-run=client -o yaml > "$CERT_DIR/k8s-secrets/$GO_SERVICE-mtls-secret.yaml"
    
    print_status "Kubernetes secrets generated"
    print_status "CA Secret: $CERT_DIR/k8s-secrets/ca-secret.yaml"
    print_status "Server TLS Secret: $CERT_DIR/k8s-secrets/$RUST_SERVICE-tls-secret.yaml"
    print_status "Client mTLS Secret: $CERT_DIR/k8s-secrets/$GO_SERVICE-mtls-secret.yaml"
}

# Generate Vault configuration
generate_vault_config() {
    print_header "Generating Vault Configuration"
    
    cat > "$CERT_DIR/vault/vault-config.hcl" << EOF
# Vault Configuration for Market Intel Brain
ui = true

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/tls/vault.crt"
  tls_key_file = "/vault/tls/vault.key"
}

storage "file" {
  path = "/vault/data"
}

api_addr = "https://vault.market-intel-brain.svc.cluster.local:8200"
cluster_addr = "https://vault.market-intel-brain.svc.cluster.local:8201"

# Enable mTLS for API
listener "tcp" {
  address = "0.0.0.0:8200"
  tls_client_ca_file = "/vault/ca/ca.crt"
  tls_require_and_verify_client_cert = "true"
}

# Enable secrets engine
secrets {
  transit = true
  kv = true
}

# Enable authentication
auth "kubernetes" {
  path = "kubernetes"
}

# Enable audit logging
audit "file" {
  path = "/vault/logs/audit.log"
  format = "json"
}
EOF
    
    print_status "Vault configuration generated"
}

# Generate certificate validation script
generate_validation_script() {
    print_header "Generating Certificate Validation Script"
    
    cat > "$CERT_DIR/validate-certs.sh" << EOF
#!/bin/bash

# Certificate Validation Script for Market Intel Brain

CERT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

validate_cert() {
    local cert_file="\$1"
    local key_file="\$2"
    local ca_file="\$3"
    local description="\$4"
    
    echo "Validating \$description..."
    
    # Check if files exist
    if [[ ! -f "\$cert_file" ]]; then
        echo "ERROR: Certificate file \$cert_file not found"
        return 1
    fi
    
    if [[ ! -f "\$key_file" ]]; then
        echo "ERROR: Key file \$key_file not found"
        return 1
    fi
    
    if [[ ! -f "\$ca_file" ]]; then
        echo "ERROR: CA file \$ca_file not found"
        return 1
    fi
    
    # Verify certificate
    if openssl verify -CAfile "\$ca_file" "\$cert_file" > /dev/null 2>&1; then
        echo "✓ Certificate is valid"
    else
        echo "✗ Certificate validation failed"
        return 1
    fi
    
    # Check certificate expiration
    local exp_date=\$(openssl x509 -in "\$cert_file" -noout -enddate | cut -d= -f2)
    local exp_timestamp=\$(date -d "\$exp_date" +%s)
    local current_timestamp=\$(date +%s)
    local days_until_expiry=\$(( (\$exp_timestamp - \$current_timestamp) / 86400 ))
    
    if [[ \$days_until_expiry -lt 30 ]]; then
        echo "⚠ Certificate expires in \$days_until_expiry days"
    else
        echo "✓ Certificate expires in \$days_until_expiry days"
    fi
    
    return 0
}

# Validate all certificates
echo "=== Certificate Validation ==="

# Validate CA
if [[ -f "\$CERT_DIR/ca/ca-cert.pem" ]]; then
    echo "✓ CA certificate exists"
else
    echo "✗ CA certificate not found"
    exit 1
fi

# Validate server certificate
validate_cert "\$CERT_DIR/server/$RUST_SERVICE-cert.pem" \
               "\$CERT_DIR/server/$RUST_SERVICE-key.pem" \
               "\$CERT_DIR/ca/ca-cert.pem" \
               "Rust Server Certificate"

# Validate client certificate
validate_cert "\$CERT_DIR/client/$GO_SERVICE-cert.pem" \
               "\$CERT_DIR/client/$GO_SERVICE-key.pem" \
               "\$CERT_DIR/ca/ca-cert.pem" \
               "Go Client Certificate"

echo "=== Validation Complete ==="
EOF
    
    chmod +x "$CERT_DIR/validate-certs.sh"
    print_status "Certificate validation script generated"
}

# Generate certificate renewal script
generate_renewal_script() {
    print_header "Generating Certificate Renewal Script"
    
    cat > "$CERT_DIR/renew-certs.sh" << EOF
#!/bin/bash

# Certificate Renewal Script for Market Intel Brain

CERT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="\$CERT_DIR/backup/\$(date +%Y%m%d_%H%M%S)"

# Create backup directory
mkdir -p "\$BACKUP_DIR"

# Backup existing certificates
if [[ -d "\$CERT_DIR/ca" ]]; then
    cp -r "\$CERT_DIR/ca" "\$BACKUP_DIR/"
fi

if [[ -d "\$CERT_DIR/server" ]]; then
    cp -r "\$CERT_DIR/server" "\$BACKUP_DIR/"
fi

if [[ -d "\$CERT_DIR/client" ]]; then
    cp -r "\$CERT_DIR/client" "\$BACKUP_DIR/"
fi

echo "Existing certificates backed up to: \$BACKUP_DIR"

# Generate new certificates
echo "Generating new certificates..."
./generate-certs.sh

echo "Certificate renewal completed"
echo "Please update Kubernetes secrets with new certificates"
EOF
    
    chmod +x "$CERT_DIR/renew-certs.sh"
    print_status "Certificate renewal script generated"
}

# Generate deployment script
generate_deployment_script() {
    print_header "Generating Certificate Deployment Script"
    
    cat > "$CERT_DIR/deploy-certs.sh" << EOF
#!/bin/bash

# Certificate Deployment Script for Market Intel Brain

CERT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

deploy_secrets() {
    echo "Deploying certificates to Kubernetes..."
    
    # Deploy CA secret
    kubectl apply -f "\$CERT_DIR/k8s-secrets/ca-secret.yaml"
    
    # Deploy server TLS secret
    kubectl apply -f "\$CERT_DIR/k8s-secrets/$RUST_SERVICE-tls-secret.yaml"
    
    # Deploy client mTLS secret
    kubectl apply -f "\$CERT_DIR/k8s-secrets/$GO_SERVICE-mtls-secret.yaml"
    
    echo "Certificates deployed successfully"
}

validate_deployment() {
    echo "Validating certificate deployment..."
    
    # Check if secrets exist
    if kubectl get secret market-intel-ca -n market-intel-brain > /dev/null 2>&1; then
        echo "✓ CA secret deployed"
    else
        echo "✗ CA secret not found"
        return 1
    fi
    
    if kubectl get secret $RUST_SERVICE-tls -n market-intel-brain > /dev/null 2>&1; then
        echo "✓ Server TLS secret deployed"
    else
        echo "✗ Server TLS secret not found"
        return 1
    fi
    
    if kubectl get secret $GO_SERVICE-mtls -n market-intel-brain > /dev/null 2>&1; then
        echo "✓ Client mTLS secret deployed"
    else
        echo "✗ Client mTLS secret not found"
        return 1
    fi
    
    echo "✓ All certificates deployed successfully"
    return 0
}

# Main execution
case "\${1:-deploy}" in
    "deploy")
        deploy_secrets
        validate_deployment
        ;;
    "validate")
        validate_deployment
        ;;
    *)
        echo "Usage: \$0 {deploy|validate}"
        exit 1
        ;;
esac
EOF
    
    chmod +x "$CERT_DIR/deploy-certs.sh"
    print_status "Certificate deployment script generated"
}

# Main execution
main() {
    print_header "Market Intel Brain Certificate Generation"
    print_status "Starting certificate generation process..."
    
    # Check if OpenSSL is available
    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL is not installed. Please install OpenSSL first."
        exit 1
    fi
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl is not installed. Kubernetes secrets will not be generated."
    fi
    
    # Create directories
    create_directories
    
    # Generate certificates
    generate_root_ca
    generate_server_cert
    generate_client_cert
    
    # Generate PKCS12 format
    generate_pkcs12
    
    # Generate Kubernetes secrets (if kubectl is available)
    if command -v kubectl &> /dev/null; then
        generate_k8s_secrets
    fi
    
    # Generate Vault configuration
    generate_vault_config
    
    # Generate utility scripts
    generate_validation_script
    generate_renewal_script
    generate_deployment_script
    
    print_header "Certificate Generation Complete"
    print_status "All certificates and configurations have been generated successfully!"
    print_status ""
    print_status "Generated files:"
    print_status "  - Root CA: $CERT_DIR/ca/"
    print_status "  - Server Certs: $CERT_DIR/server/"
    print_status "  - Client Certs: $CERT_DIR/client/"
    print_status "  - Kubernetes Secrets: $CERT_DIR/k8s-secrets/"
    print_status "  - Vault Config: $CERT_DIR/vault/"
    print_status ""
    print_status "Utility scripts:"
    print_status "  - Validation: $CERT_DIR/validate-certs.sh"
    print_status "  - Renewal: $CERT_DIR/renew-certs.sh"
    print_status "  - Deployment: $CERT_DIR/deploy-certs.sh"
    print_status ""
    print_status "Next steps:"
    print_status "  1. Validate certificates: ./validate-certs.sh"
    print_status "  2. Deploy to Kubernetes: ./deploy-certs.sh"
    print_status "  3. Update service configurations to use mTLS"
    print_status "  4. Test secure gRPC communication"
}

# Run main function
main "$@"
