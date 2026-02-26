// TLS Configuration and mTLS Support for API Gateway
// This package provides TLS configuration for gRPC client with mutual TLS (mTLS) support.

package tls

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"io/ioutil"
	"os"
	"time"
)

// TLSConfig holds TLS configuration
type TLSConfig struct {
	CertFile   string
	KeyFile    string
	CAFile     string
	ServerName string
	SkipVerify bool
}

// CertificateInfo holds certificate information
type CertificateInfo struct {
	Subject      string    `json:"subject"`
	Issuer       string    `json:"issuer"`
	NotBefore    time.Time `json:"not_before"`
	NotAfter     time.Time `json:"not_after"`
	IsExpired    bool      `json:"is_expired"`
	DaysUntilExp int64     `json:"days_until_expiration"`
}

// LoadTLSConfig loads TLS configuration from files
func LoadTLSConfig(certFile, keyFile, caFile, serverName string, skipVerify bool) (*TLSConfig, error) {
	config := &TLSConfig{
		CertFile:   certFile,
		KeyFile:    keyFile,
		CAFile:     caFile,
		ServerName: serverName,
		SkipVerify: skipVerify,
	}

	// Validate file existence
	if _, err := os.Stat(certFile); os.IsNotExist(err) {
		return nil, fmt.Errorf("certificate file not found: %s", certFile)
	}
	if _, err := os.Stat(keyFile); os.IsNotExist(err) {
		return nil, fmt.Errorf("key file not found: %s", keyFile)
	}
	if caFile != "" {
		if _, err := os.Stat(caFile); os.IsNotExist(err) {
			return nil, fmt.Errorf("CA file not found: %s", caFile)
		}
	}

	return config, nil
}

// CreateTLSClientConfig creates TLS client configuration
func (config *TLSConfig) CreateTLSClientConfig() (*tls.Config, error) {
	tlsConfig := &tls.Config{
		ServerName:         config.ServerName,
		InsecureSkipVerify: config.SkipVerify,
	}

	// Load client certificate
	if config.CertFile != "" && config.KeyFile != "" {
		cert, err := tls.LoadX509KeyPair(config.CertFile, config.KeyFile)
		if err != nil {
			return nil, fmt.Errorf("failed to load client certificate: %w", err)
		}
		tlsConfig.Certificates = []tls.Certificate{cert}
	}

	// Load CA certificate
	if config.CAFile != "" {
		caCert, err := ioutil.ReadFile(config.CAFile)
		if err != nil {
			return nil, fmt.Errorf("failed to read CA certificate: %w", err)
		}

		caCertPool := x509.NewCertPool()
		if !caCertPool.AppendCertsFromPEM(caCert) {
			return nil, fmt.Errorf("failed to parse CA certificate")
		}
		tlsConfig.RootCAs = caCertPool
	}

	return tlsConfig, nil
}

// ParseCertificate parses certificate and extracts information
func ParseCertificate(certPath string) (*CertificateInfo, error) {
	data, err := ioutil.ReadFile(certPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read certificate file: %w", err)
	}

	block, _ := pem.Decode(data)
	if block == nil {
		return nil, fmt.Errorf("failed to decode PEM certificate")
	}

	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse certificate: %w", err)
	}

	now := time.Now()
	info := &CertificateInfo{
		Subject:   cert.Subject.CommonName,
		Issuer:    cert.Issuer.CommonName,
		NotBefore: cert.NotBefore,
		NotAfter:  cert.NotAfter,
		IsExpired: now.After(cert.NotAfter),
	}

	if !info.IsExpired {
		info.DaysUntilExp = int64(cert.NotAfter.Sub(now).Hours() / 24)
	}

	return info, nil
}

// ValidateCertificate checks if certificate is valid
func ValidateCertificate(certPath string) error {
	info, err := ParseCertificate(certPath)
	if err != nil {
		return err
	}

	if info.IsExpired {
		return fmt.Errorf("certificate has expired on %s", info.NotAfter.Format(time.RFC3339))
	}

	if info.DaysUntilExp < 30 {
		return fmt.Errorf("certificate will expire in %d days", info.DaysUntilExp)
	}

	return nil
}

// Get days until expiration
func (info *CertificateInfo) DaysUntilExpiration() int64 {
	return int64(info.NotAfter.Sub(time.Now()).Hours() / 24)
}
