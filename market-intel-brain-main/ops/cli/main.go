// Market Intel Brain Operations CLI Tool
// Provides automated runbooks and operations tooling for common incidents

package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"gopkg.in/yaml.v3"
)

// Configuration structure
type Config struct {
	Namespace     string `yaml:"namespace"`
	DebugImage    string `yaml:"debug_image"`
	DebugTTL      int    `yaml:"debug_ttl"`
	BackupDir     string `yaml:"backup_dir"`
	ReportsDir    string `yaml:"reports_dir"`
	ScriptsDir    string `yaml:"scripts_dir"`
}

// Certificate rotation configuration
type CertConfig struct {
	Name         string `yaml:"name"`
	SecretName   string `yaml:"secret_name"`
	CertManager  bool   `yaml:"cert_manager"`
	Vault        bool   `yaml:"vault"`
	Backup       bool   `yaml:"backup"`
}

// Redis cache configuration
type RedisConfig struct {
	Name     string `yaml:"name"`
	Pattern  string `yaml:"pattern"`
	Backup   bool   `yaml:"backup"`
}

// Global variables
var (
	config      Config
	certConfigs []CertConfig
	redisConfigs []RedisConfig
)

// Root command
var rootCmd = &cobra.Command{
	Use:   "ops-cli",
	Short: "Market Intel Brain Operations CLI",
	Long:  `Automated runbooks and operations tooling for Market Intel Brain`,
	PersistentPreRun: func(cmd *cobra.Command, args []string) {
		loadConfig()
	},
}

// Certificate rotation command
var certCmd = &cobra.Command{
	Use:   "cert",
	Short: "Certificate rotation operations",
	Long:  `Rotate certificates in Vault/Cert-Manager with zero downtime`,
}

var certRotateCmd = &cobra.Command{
	Use:   "rotate [certificate-name]",
	Short: "Rotate a certificate",
	Long:  `Rotate a specific certificate with backup and verification`,
	Args:  cobra.ExactArgs(1),
	RunE:  runCertRotate,
}

var certListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all certificates",
	Long:  `List all configured certificates with their status`,
	RunE: runCertList,
}

var certValidateCmd = &cobra.Command{
	Use:   "validate [certificate-name]",
	Short: "Validate a certificate",
	Long:  `Validate certificate expiration and configuration`,
	Args:  cobra.ExactArgs(1),
	RunE: runCertValidate,
}

// Redis operations command
var redisCmd = &cobra.Command{
	Use:   "redis",
	Short: "Redis cache operations",
	Long:  `Safely manage Redis cache without downtime`,
}

var redisFlushCmd = &cobra.Command{
	Use:   "flush [cache-type|pattern]",
	Short: "Flush Redis cache",
	Long:  `Safely flush specific Redis cache keys with backup`,
	Args:  cobra.ExactArgs(1),
	RunE: runRedisFlush,
}

var redisStatsCmd = &cobra.Command{
	Use:   "stats",
	Short: "Show Redis statistics",
	Long:  `Display Redis cache statistics and key counts`,
	RunE: runRedisStats,
}

var redisBackupCmd = &cobra.Command{
	Use:   "backup [pattern]",
	Short: "Backup Redis data",
	Long:  `Backup Redis data matching a pattern`,
	Args:  cobra.ExactArgs(1),
	RunE: runRedisBackup,
}

// Debug operations command
var debugCmd = &cobra.Command{
	Use:   "debug",
	Short: "Debug pod operations",
	Long:  `Launch debug containers attached to production pods`,
}

var debugCreateCmd = &cobra.Command{
	Use:   "create [pod-name]",
	Short: "Create debug pod",
	Long:  `Create ephemeral debug container attached to target pod`,
	Args:  cobra.ExactArgs(1),
	RunE: runDebugCreate,
}

var debugInteractiveCmd = &cobra.Command{
	Use:   "interactive [pod-name]",
	Short: "Start interactive debug session",
	Long:  `Start interactive shell in debug pod`,
	Args:  cobra.ExactArgs(1),
	RunE: runDebugInteractive,
}

var debugCleanupCmd = &cobra.Command{
	Use:   "cleanup",
	Short: "Clean up debug pods",
	Long:  `Remove all debug pods`,
	RunE: runDebugCleanup,
}

// Initialize CLI
func init() {
	// Configuration flags
	rootCmd.PersistentFlags().StringVar(&config.Namespace, "namespace", "market-intel-brain", "Kubernetes namespace")
	rootCmd.PersistentFlags().StringVar(&config.DebugImage, "debug-image", "nicolaka/netshoot", "Debug container image")
	rootCmd.PersistentFlags().IntVar(&config.DebugTTL, "debug-ttl", 3600, "Debug pod TTL in seconds")
	rootCmd.PersistentFlags().StringVar(&config.BackupDir, "backup-dir", "./backups", "Backup directory")
	rootCmd.PersistentFlags().StringVar(&config.ReportsDir, "reports-dir", "./reports", "Reports directory")
	rootCmd.PersistentFlags().StringVar(&config.ScriptsDir, "scripts-dir", "./scripts", "Scripts directory")

	// Certificate flags
	certRotateCmd.Flags().String("method", "auto", "Rotation method (auto, cert-manager, vault)")
	certRotateCmd.Flags().Bool("force", false, "Force rotation without confirmation")

	// Redis flags
	redisFlushCmd.Flags().Bool("force", false, "Force flush without confirmation")
	redisFlushCmd.Flags().Int("batch-size", 100, "Batch size for key deletion")

	// Debug flags
	debugCreateCmd.Flags().String("image", "", "Custom debug image (overrides config)")
	debugCreateCmd.Flags().Int("ttl", 0, "Debug pod TTL in seconds (overrides config)")

	// Add subcommands
	rootCmd.AddCommand(certCmd)
	certCmd.AddCommand(certRotateCmd)
	certCmd.AddCommand(certListCmd)
	certCmd.AddCommand(certValidateCmd)

	rootCmd.AddCommand(redisCmd)
	redisCmd.AddCommand(redisFlushCmd)
	redisCmd.AddCommand(redisStatsCmd)
	redisCmd.AddCommand(redisBackupCmd)

	rootCmd.AddCommand(debugCmd)
	debugCmd.AddCommand(debugCreateCmd)
	debugCmd.AddCommand(debugInteractiveCmd)
	debugCmd.AddCommand(debugCleanupCmd)

	// Bind flags
	viper.BindPFlag(rootCmd.PersistentFlags().Lookup("namespace"))
	viper.BindPFlag(rootCmd.PersistentFlags().Lookup("debug-image"))
	viper.BindPFlag(rootCmd.PersistentFlags().Lookup("debug-ttl"))
	viper.BindPFlag(rootCmd.PersistentFlags().Lookup("backup-dir"))
	viper.BindPFlag(rootCmd.PersistentFlags().Lookup("reports-dir"))
	viper.BindPFlag(rootCmd.PersistentFlags().Lookup("scripts-dir"))
}

// Load configuration
func loadConfig() {
	// Load config file if exists
	configFile := filepath.Join(config.ScriptsDir, "config.yaml")
	if _, err := os.Stat(configFile); err == nil {
		data, err := os.ReadFile(configFile)
		if err != nil {
			fmt.Printf("Error reading config file: %v\n", err)
			os.Exit(1)
		}

		if err := yaml.Unmarshal(data, &config); err != nil {
			fmt.Printf("Error parsing config file: %v\n", err)
			os.Exit(1)
		}
	}

	// Load certificate configurations
	certConfigFile := filepath.Join(config.ScriptsDir, "certs.yaml")
	if _, err := os.Stat(certConfigFile); err == nil {
		data, err := os.ReadFile(certConfigFile)
		if err != nil {
			fmt.Printf("Error reading cert config file: %v\n", err)
			os.Exit(1)
		}

		if err := yaml.Unmarshal(data, &certConfigs); err != nil {
			fmt.Printf("Error parsing cert config file: %v\n", err)
			os.Exit(1)
		}
	}

	// Load Redis configurations
	redisConfigFile := filepath.Join(config.ScriptsDir, "redis.yaml")
	if _, err := os.Stat(redisConfigFile); err == nil {
		data, err := os.ReadFile(redisConfigFile)
		if err != nil {
			fmt.Printf("Error reading redis config file: %v\n", err)
			os.Exit(1)
		}

		if err := yaml.Unmarshal(data, &redisConfigs); err != nil {
			fmt.Printf("Error parsing redis config file: %v\n", err)
			os.Exit(1)
		}
	}

	// Set defaults
	if config.Namespace == "" {
		config.Namespace = "market-intel-brain"
	}
	if config.DebugImage == "" {
		config.DebugImage = "nicolaka/netshoot"
	}
	if config.DebugTTL == 0 {
		config.DebugTTL = 3600
	}
	if config.BackupDir == "" {
		config.BackupDir = "./backups"
	}
	if config.ReportsDir == "" {
		config.ReportsDir = "./reports"
	}
	if config.ScriptsDir == "" {
		config.ScriptsDir = "./scripts"
	}
}

// Run certificate rotation
func runCertRotate(cmd *cobra.Command, args []string) error {
	certName := args[0]
	method := viper.GetString("method")
	force := viper.GetBool("force")

	fmt.Printf("Rotating certificate: %s\n", certName)
	fmt.Printf("Method: %s\n", method)
	fmt.Printf("Force: %t\n", force)

	// Find certificate configuration
	var certConfig *CertConfig
	for i, cert := range certConfigs {
		if cert.Name == certName {
			certConfig = &certConfigs[i]
			break
		}
	}

	if certConfig == nil {
		return fmt.Errorf("certificate not found: %s", certName)
	}

	// Execute rotation script
	scriptPath := filepath.Join(config.ScriptsDir, "rotate-certs.sh")
	cmd := exec.Command(scriptPath, "rotate", certName, method)

	if force {
		cmd.Env = append(os.Environ(), "FORCE_FLUSH=true")
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Error rotating certificate: %v\n", err)
		fmt.Printf("Output: %s\n", string(output))
		return err
	}

	fmt.Printf("Certificate rotation completed:\n%s\n", string(output))
	return nil
}

// Run certificate list
func runCertList(cmd *cobra.Command, args []string) error {
	fmt.Println("Available certificates:")

	for _, cert := range certConfigs {
		fmt.Printf("  - %s (Secret: %s)\n", cert.Name, cert.SecretName)
		fmt.Printf("    CertManager: %t, Vault: %t, Backup: %t\n", cert.CertManager, cert.Vault, cert.Backup)
	}

	return nil
}

// Run certificate validation
func runCertValidate(cmd *cobra.Command, args []string) error {
	certName := args[0]

	fmt.Printf("Validating certificate: %s\n", certName)

	// Execute validation script
	scriptPath := filepath.Join(config.ScriptsDir, "rotate-certs.sh")
	cmd := exec.Command(scriptPath, "validate", certName)

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Error validating certificate: %v\n", err)
		fmt.Printf("Output: %s\n", string(output))
		return err
	}

	fmt.Printf("Certificate validation:\n%s\n", string(output))
	return nil
}

// Run Redis flush
func runRedisFlush(cmd *cobra.Command, args []string) error {
	cacheType := args[0]
	force := viper.GetBool("force")
	batchSize := viper.GetInt("batch-size")

	fmt.Printf("Flushing Redis cache: %s\n", cacheType)
	fmt.Printf("Force: %t\n", force)
	fmt.Printf("Batch size: %d\n", batchSize)

	// Check if it's a custom pattern or predefined type
	var pattern string
	isCustom := false

	for _, redisConfig := range redisConfigs {
		if redisConfig.Name == cacheType {
			pattern = redisConfig.Pattern
			break
		}
	}

	if pattern == "" {
		// Assume it's a custom pattern
		pattern = cacheType
		isCustom = true
	}

	// Execute flush script
	scriptPath := filepath.Join(config.ScriptsDir, "flush-redis.sh")
	var cmd *exec.Cmd

	if isCustom {
		cmd = exec.Command(scriptPath, "flush", "custom", pattern)
	} else {
		cmd = exec.Command(scriptPath, "flush", cacheType)
	}

	if force {
		cmd.Env = append(os.Environ(), "FORCE_FLUSH=true")
	}

	cmd.Env = append(cmd.Env, fmt.Sprintf("BATCH_SIZE=%d", batchSize))

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Error flushing Redis: %v\n", err)
		fmt.Printf("Output: %s\n", string(output))
		return err
	}

	fmt.Printf("Redis flush completed:\n%s\n", string(output))
	return nil
}

// Run Redis stats
func runRedisStats(cmd *cobra.Command, args []string) error {
	fmt.Println("Redis statistics:")

	// Execute stats script
	scriptPath := filepath.Join(config.ScriptsDir, "flush-redis.sh")
	cmd := exec.Command(scriptPath, "stats")

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Error getting Redis stats: %v\n", err)
		fmt.Printf("Output: %s\n", string(output))
		return err
	}

	fmt.Printf("Redis statistics:\n%s\n", string(output))
	return nil
}

// Run Redis backup
func runRedisBackup(cmd *cobra.Command, args []string) error {
	pattern := args[0]

	fmt.Printf("Backing up Redis data: %s\n", pattern)

	// Execute backup script
	scriptPath := filepath.Join(config.ScriptsDir, "flush-redis.sh")
	cmd := exec.Command(scriptPath, "backup", pattern)

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Error backing up Redis: %v\n", err)
		fmt.Printf("Output: %s\n", string(output))
		return err
	}

	fmt.Printf("Redis backup completed:\n%s\n", string(output))
	return nil
}

// Run debug create
func runDebugCreate(cmd *cobra.Command, args []string) error {
	podName := args[0]
	image := viper.GetString("image")
	ttl := viper.GetInt("ttl")

	fmt.Printf("Creating debug pod for: %s\n", podName)
	if image != "" {
		fmt.Printf("Image: %s\n", image)
	}
	if ttl > 0 {
		fmt.Printf("TTL: %d seconds\n", ttl)
	}

	// Execute debug script
	scriptPath := filepath.Join(config.ScriptsDir, "debug-pod.sh")
	cmdArgs := []string{"create", podName}

	if image != "" {
		cmdArgs = append(cmdArgs, image)
	}

	if ttl > 0 {
		cmdArgs = append(cmdArgs, fmt.Sprintf("--ttl=%d", ttl))
	}

	cmd := exec.Command(scriptPath, cmdArgs...)

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Error creating debug pod: %v\n", err)
		fmt.Printf("Output: %s\n", string(output))
		return err
	}

	fmt.Printf("Debug pod created:\n%s\n", string(output))
	return nil
}

// Run debug interactive
func runDebugInteractive(cmd *cobra.Command, args []string) error {
	podName := args[0]

	fmt.Printf("Starting interactive debug session for: %s\n", podName)

	// Execute debug script
	scriptPath := filepath.Join(config.ScriptsDir, "debug-pod.sh")
	cmd := exec.Command(scriptPath, "interactive", podName)

	// Run interactive session
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		fmt.Printf("Error in debug session: %v\n", err)
		return err
	}

	return nil
}

// Run debug cleanup
func runDebugCleanup(cmd *cobra.Command, args []string) error {
	fmt.Println("Cleaning up debug pods...")

	// Execute debug script
	scriptPath := filepath.Join(config.ScriptsDir, "debug-pod.sh")
	cmd := exec.Command(scriptPath, "cleanup")

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Error cleaning up debug pods: %v\n", err)
		fmt.Printf("Output: %s\n", string(output))
		return err
	}

	fmt.Printf("Debug cleanup completed:\n%s\n", string(output))
	return nil
}

// Execute shell command with timeout
func executeCommand(ctx context.Context, command string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, command, args...)
	
	var stdout, stderr strings.Builder
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	
	err := cmd.Run()
	if err != nil {
		return "", fmt.Errorf("command failed: %v, stderr: %s", err, stderr.String())
	}
	
	return stdout.String(), nil
}

// Read user input with timeout
func readInputWithTimeout(prompt string, timeout time.Duration) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	
	fmt.Print(prompt)
	
	done := make(chan string)
	go func() {
		reader := bufio.NewReader(os.Stdin)
		input, _ := reader.ReadString('\n')
		done <- strings.TrimSpace(input)
	}()
	
	select {
	case input := <-done:
		return input, nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}

// Generate report
func generateReport(reportType string, data interface{}) error {
	reportDir := filepath.Join(config.ReportsDir, time.Now().Format("20060102_150405"))
	if err := os.MkdirAll(reportDir, 0755); err != nil {
		return fmt.Errorf("failed to create report directory: %v", err)
	}
	
	reportFile := filepath.Join(reportDir, fmt.Sprintf("%s-report.json", reportType))
	
	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal report data: %v", err)
	}
	
	if err := os.WriteFile(reportFile, jsonData, 0644); err != nil {
		return fmt.Errorf("failed to write report file: %v", err)
	}
	
	fmt.Printf("Report generated: %s\n", reportFile)
	return nil
}

// Main function
func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}
}
