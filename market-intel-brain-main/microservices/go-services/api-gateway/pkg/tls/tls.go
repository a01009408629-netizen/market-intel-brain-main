// TLS Configuration and mTLS Support for API Gateway
// This package provides TLS configuration for gRPC client with mutual TLS (mTLS) support.

package tls

import (
	"crypto/tls"
	"crypto/x509"
	"io/ioutil"
	"os"
	"strings"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"github.com/market-intel/api-gateway/pkg/logger"
)

// TLS configuration for gRPC client
type TLSConfig struct {
	// Path to the client certificate file
	ClientCertPath string `json:"client_cert_path" yaml:"client_cert_path"`
	
	// Path to the client private key file
	ClientKeyPath string `json:"client_key_path" yaml:"client_key_path"`
	
	// Path to the CA certificate file for server verification
	CACertPath string `json:"ca_cert_path" yaml:"ca_cert_path"`
	
	// Whether to verify server certificate
	VerifyServerCert bool `json:"verify_server_cert" yaml:"verify_server_cert"`
	
	// Server name for certificate verification
	ServerName string `json:"server_name" yaml:"server_name"`
	
	// Skip TLS verification (for testing only)
	SkipVerify bool `json:"skip_verify" yaml:"skip_verify"`
}

// Default TLS configuration
func DefaultTLSConfig() *TLSConfig {
	return &TLSConfig{
		ClientCertPath:    "/etc/tls/client.crt",
		ClientKeyPath:     "/etc/tls/client.key",
		CACertPath:        "/etc/tls/ca.crt",
		VerifyServerCert:   true,
		ServerName:         "core-engine.market-intel-brain.svc.cluster.local",
		SkipVerify:        false,
	}
}

// Create TLS configuration from environment variables
func NewTLSConfigFromEnv() *TLSConfig {
	config := DefaultTLSConfig()
	
	if certPath := os.Getenv("CLIENT_CERT_PATH"); certPath != "" {
		config.ClientCertPath = certPath
	}
	
	if keyPath := os.Getenv("CLIENT_KEY_PATH"); keyPath != "" {
		config.ClientKeyPath = keyPath
	}
	
	if caPath := os.Getenv("CA_CERT_PATH"); caPath != "" {
		config.CACertPath = caPath
	}
	
	if verify := os.Getenv("VERIFY_SERVER_CERT"); verify != "" {
		config.VerifyServerCert = strings.ToLower(verify) == "true"
	}
	
	if serverName := os.Getenv("SERVER_NAME"); serverName != "" {
		config.ServerName = serverName
	}
	
	if skip := os.Getenv("SKIP_TLS_VERIFY"); skip != "" {
		config.SkipVerify = strings.ToLower(skip) == "true"
	}
	
	return config
}

// Load client certificate and key
func (c *TLSConfig) LoadClientCertificate() (tls.Certificate, error) {
	cert, err := ioutil.ReadFile(c.ClientCertPath)
	if err != nil {
		return tls.Certificate{}, logger.Errorf("failed to read client certificate: %w", err)
	}
	
	key, err := ioutil.ReadFile(c.ClientKeyPath)
	if err != nil {
		return tls.Certificate{}, logger.Errorf("failed to read client private key: %w", err)
	}
	
	clientCert, err := tls.X509KeyPair(cert, key)
	if err != nil {
		return tls.Certificate{}, logger.Errorf("failed to parse client certificate: %w", err)
	}
	
	logger.Infof("Client certificate loaded successfully from %s", c.ClientCertPath)
	return clientCert, nil
}

// Load CA certificate for server verification
func (c *TLSConfig) LoadCACertificate() (*x509.CertPool, error) {
	caCert, err := ioutil.ReadFile(c.CACertPath)
	if err != nil {
		return nil, logger.Errorf("failed to read CA certificate: %w", err)
	}
	
	certPool := x509.NewCertPool()
	if !certPool.AppendCertsFromPEM(caCert) {
		return nil, logger.Errorf("failed to parse CA certificate")
	}
	
	logger.Infof("CA certificate loaded successfully from %s", c.CACertPath)
	return certPool, nil
}

// Create TLS configuration for gRPC client
func (c *TLSConfig) CreateTLSConfig() (*tls.Config, error) {
	logger.Infof("Creating TLS configuration for gRPC client")
	logger.Infof("Client certificate path: %s", c.ClientCertPath)
	logger.Infof("Client key path: %s", c.ClientKeyPath)
	logger.Infof("CA certificate path: %s", c.CACertPath)
	logger.Infof("Server name: %s", c.ServerName)
	logger.Infof("Verify server cert: %t", c.VerifyServerCert)
	logger.Infof("Skip verify: %t", c.SkipVerify)

	// Load client certificate
	clientCert, err := c.LoadClientCertificate()
	if err != nil {
		return nil, logger.Errorf("failed to load client certificate: %w", err)
	}

	// Load CA certificate
	var certPool *x509.CertPool
	if c.VerifyServerCert && !c.SkipVerify {
		certPool, err = c.LoadCACertificate()
		if err != nil {
			return nil, logger.Errorf("failed to load CA certificate: %w", err)
		}
	}

	// Create TLS configuration
	tlsConfig := &tls.Config{
		Certificates: []tls.Certificate{clientCert},
		RootCAs:    certPool,
		ServerName:  c.ServerName,
		MinVersion: tls.VersionTLS12,
		MaxVersion: tls.VersionTLS13,
		
		// Cipher suites for security
		CipherSuites: []uint16{
			tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
			tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
			tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
			tls.TLS_AES_128_GCM_SHA256,
			tls.TLS_AES_256_GCM_SHA384,
			tls.TLS_CHACHA20_POLY1305_SHA256,
		},
		
		// Curve preferences
		CurvePreferences: []tls.CurveID{
			tls.X25519,
			tls.CurveP256,
			tls.CurveP384,
			tls.CurveP521,
		},
		
		// Renegotiation
		Renegotiation: tls.RenegotiateNever,
		
		// Client authentication
		ClientAuth: tls.RequireAndVerifyClientCert,
		
		// InsecureSkipVerify for testing only
		InsecureSkipVerify: c.SkipVerify,
	}

	logger.Infof("TLS configuration created successfully")
	return tlsConfig, nil
}

// Create gRPC credentials with TLS
func (c *TLSConfig) CreateGRPCredentials() (credentials.TransportCredentials, error) {
	tlsConfig, err := c.CreateTLSConfig()
	if err != nil {
		return nil, logger.Errorf("failed to create TLS config: %w", err)
	}

	grpcCreds := credentials.NewTLS(tlsConfig)
	if grpcCreds == nil {
		return nil, logger.Errorf("failed to create gRPC credentials")
	}

	logger.Infof("gRPC credentials created successfully")
	return grpcCreds, nil
}

// Validate TLS configuration
func (c *TLSConfig) Validate() error {
	logger.Infof("Validating TLS configuration")

	// Check if certificate files exist
	if _, err := os.Stat(c.ClientCertPath); os.IsNotExist(err) {
		return logger.Errorf("client certificate file not found: %s", c.ClientCertPath)
	}

	if _, err := os.Stat(c.ClientKeyPath); os.IsNotExist(err) {
		return logger.Errorf("client private key file not found: %s", c.ClientKeyPath)
	}

	if c.VerifyServerCert && !c.SkipVerify {
		if _, err := os.Stat(c.CACertPath); os.IsNotExist(err) {
			return logger.Errorf("CA certificate file not found: %s", c.CACertPath)
		}
	}

	// Validate certificate format
	clientCert, err := c.LoadClientCertificate()
	if err != nil {
		return logger.Errorf("failed to load client certificate: %w", err)
	}

	// Parse certificate to validate format
	if len(clientCert.Certificate) == 0 {
		return logger.Errorf("client certificate is empty")
	}

	// Validate certificate expiration
	if len(clientCert.Certificate) > 0 {
		cert := clientCert.Certificate[0]
		if time.Now().After(cert.NotAfter) {
			return logger.Errorf("client certificate has expired on %s", cert.NotAfter.Format(time.RFC3339))
		}
		
		// Warn if certificate expires soon
		if time.Until(cert.NotAfter).Hours() < 24*30 { // 30 days
			logger.Warnf("client certificate expires in %.1f days", time.Until(cert.NotAfter).Hours()/24)
		}
	}

	// Validate CA certificate if verification is enabled
	if c.VerifyServerCert && !c.SkipVerify {
		_, err := c.LoadCACertificate()
		if err != nil {
			return logger.Errorf("failed to load CA certificate: %w", err)
		}
	}

	logger.Infof("TLS configuration validation successful")
	return nil
}

// Get certificate information
func (c *TLSConfig) GetCertificateInfo() (*CertificateInfo, error) {
	clientCert, err := c.LoadClientCertificate()
	if err != nil {
		return nil, logger.Errorf("failed to load client certificate: %w", err)
	}

	if len(clientCert.Certificate) == 0 {
		return nil, logger.Errorf("no certificate found")
	}

	cert := clientCert.Certificate[0]
	x509Cert, err := x509.ParseCertificate(cert)
	if err != nil {
		return nil, logger.Errorf("failed to parse certificate: %w", err)
	}

	info := &CertificateInfo{
		Subject:           x509Cert.Subject.CommonName,
		Issuer:            x509Cert.Issuer.CommonName,
		SerialNumber:       x509Cert.SerialNumber.String(),
		NotBefore:         x509Cert.NotBefore.Format(time.RFC3339),
		NotAfter:          x509Cert.NotAfter.Format(time.RFC3339),
		Version:           x509Cert.Version,
		SignatureAlgorithm: x509Cert.SignatureAlgorithm.String(),
		DNSNames:          x509Cert.DNSNames,
		EmailAddresses:     x509Cert.EmailAddresses,
		IPAddresses:        x509Cert.IPAddresses,
	}

	return info, nil
}

// Certificate information
type CertificateInfo struct {
	Subject           string    `json:"subject"`
	Issuer            string    `json:"issuer"`
	SerialNumber       string    `json:"serial_number"`
	NotBefore         string    `json:"not_before"`
	NotAfter          string    `json:"not_after"`
	Version           int       `json:"version"`
	SignatureAlgorithm string    `json:"signature_algorithm"`
	DNSNames          []string  `json:"dns_names"`
	EmailAddresses     []string  `json:"email_addresses"`
	IPAddresses       []string  `json:"ip_addresses"`
}

// Check if certificate is expired
func (info *CertificateInfo) IsExpired() bool {
	if notAfter, err := time.Parse(time.RFC3339, info.NotAfter); err == nil {
		return time.Now().After(notAfter)
	}
	return true
}

// Get days until expiration
func (info *CertificateInfo) DaysUntilExpiration() int64 {
	if notAfter, err := time.Parse(time.RFC3339, info.NotAfter); err == nil {
		return int64(notAfter.Sub(time.Now()).Hours() / 24)
	}
	return 0
}

// TLS utilities
package utils

import (
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"time"

	"github.com/market-intel/api-gateway/pkg/logger"
)

// Load certificate chain from PEM file
func LoadCertificateChain(certPath string) ([]*x509.Certificate, error) {
	data, err := ioutil.ReadFile(certPath)
	if err != nil {
		return nil, logger.Errorf("failed to read certificate file: %w", err)
	}

	var certs []*x509.Certificate
	var block *pem.Block
	var rest = data

	for {
		block, rest = pem.Decode(rest)
		if block == nil {
			break
		}

		if block.Type == "CERTIFICATE" {
			cert, err := x509.ParseCertificate(block.Bytes)
			if err != nil {
				return nil, logger.Errorf("failed to parse certificate: %w", err)
			}
			certs = append(certs, cert)
		}
	}

	if len(certs) == 0 {
		return nil, fmt.Errorf("no certificates found in %s", certPath)
	}

	logger.Infof("Loaded %d certificates from %s", len(certs), certPath)
	return certs, nil
}

// Validate certificate chain
func ValidateCertificateChain(certs []*x509.Certificate, caCertPath string) error {
	if len(certs) == 0 {
		return fmt.Errorf("no certificates to validate")
	}

	caData, err := ioutil.ReadFile(caCertPath)
	if err != nil {
		return logger.Errorf("failed to read CA certificate: %w", err)
	}

	caCert, err := x509.ParseCertificate(caData)
	if err != nil {
		return logger.Errorf("failed to parse CA certificate: %w", err)
	}

	// Create certificate pool
	roots := x509.NewCertPool()
	roots.AddCert(caCert)

	// Verify each certificate in the chain
	for i, cert := range certs {
		opts := x509.VerifyOptions{
			Roots:     roots,
			CurrentTime: time.Now(),
			KeyUsages:  []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth},
		}

		if _, err := cert.Verify(opts); err != nil {
			return logger.Errorf("certificate %d validation failed: %w", i+1, err)
		}
	}

	logger.Infof("Certificate chain validation successful for %d certificates", len(certs))
	return nil
}

// Generate certificate fingerprint
func GenerateFingerprint(cert *x509.Certificate) string {
	hash := sha256.Sum256(cert.Raw)
	return fmt.Sprintf("%x", hash)
}

// Check certificate revocation (placeholder)
func CheckRevocation(cert *x509.Certificate) (bool, error) {
	// In production, implement CRL or OCSP checking
	logger.Warn("Certificate revocation checking not implemented - always returns false")
	return false, nil
}
