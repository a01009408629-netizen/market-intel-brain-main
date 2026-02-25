// Circuit Breaker Implementation for gRPC Client
// Provides circuit breaker pattern with exponential backoff and retry logic

package resilience

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"sync"
	"sync/atomic"
	"time"

	"github.com/market-intel/api-gateway/pkg/logger"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// Circuit breaker states
type CircuitState int32

const (
	StateClosed CircuitState = iota
	StateOpen
	StateHalfOpen
)

// Circuit breaker configuration
type CircuitBreakerConfig struct {
	// Maximum number of failures before opening circuit
	MaxFailures int `json:"max_failures" yaml:"max_failures"`
	
	// Timeout for half-open state
	Timeout time.Duration `json:"timeout" yaml:"timeout"`
	
	// Reset timeout for open state
	ResetTimeout time.Duration `json:"reset_timeout" yaml:"reset_timeout"`
	
	// Whether to enable metrics
	EnableMetrics bool `json:"enable_metrics" yaml:"enable_metrics"`
}

// Default circuit breaker configuration
func DefaultCircuitBreakerConfig() *CircuitBreakerConfig {
	return &CircuitBreakerConfig{
		MaxFailures:   5,
		Timeout:        30 * time.Second,
		ResetTimeout:   60 * time.Second,
		EnableMetrics: true,
	}
}

// Circuit breaker implementation
type CircuitBreaker struct {
	config           *CircuitBreakerConfig
	state            int32
	failures         int64
	lastFailureTime  int64
	generation       int64
	mu              sync.RWMutex
	metrics          *CircuitBreakerMetrics
}

// Circuit breaker metrics
type CircuitBreakerMetrics struct {
	RequestsTotal      int64
	SuccessesTotal    int64
	FailuresTotal     int64
	CircuitOpensTotal int64
	CircuitClosesTotal int64
	TimeoutsTotal     int64
}

// Create new circuit breaker
func NewCircuitBreaker(config *CircuitBreakerConfig) *CircuitBreaker {
	if config == nil {
		config = DefaultCircuitBreakerConfig()
	}
	
	cb := &CircuitBreaker{
		config:  config,
		state:   int32(StateClosed),
		metrics: &CircuitBreakerMetrics{},
	}
	
	if config.EnableMetrics {
		logger.Infof("Circuit breaker initialized with metrics enabled")
	}
	
	return cb
}

// Execute function with circuit breaker protection
func (cb *CircuitBreaker) Execute(ctx context.Context, fn func() error) error {
	// Check if circuit is open
	if cb.isOpen() {
		cb.recordRequest()
		cb.recordFailure()
		return fmt.Errorf("circuit breaker is open")
	}
	
	// Check if circuit is half-open
	if cb.isHalfOpen() {
		cb.recordRequest()
		// Allow single request through in half-open state
		err := fn()
		if err != nil {
			cb.recordFailure()
			cb.open()
		} else {
			cb.recordSuccess()
			cb.close()
		}
		return err
	}
	
	// Circuit is closed, allow request through
	cb.recordRequest()
	err := fn()
	if err != nil {
		cb.recordFailure()
		cb.checkThresholds()
	} else {
		cb.recordSuccess()
	}
	
	return err
}

// Check if circuit is open
func (cb *CircuitBreaker) isOpen() bool {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	
	if cb.state == int32(StateOpen) {
		// Check if reset timeout has passed
		lastFailure := time.Unix(atomic.LoadInt64(&cb.lastFailureTime), 0)
		if time.Since(lastFailure) > cb.config.ResetTimeout {
			logger.Infof("Circuit breaker reset timeout reached, closing circuit")
			cb.close()
			return false
		}
		return true
	}
	
	return false
}

// Check if circuit is half-open
func (cb *CircuitBreaker) isHalfOpen() bool {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state == int32(StateHalfOpen)
}

// Check if circuit is closed
func (cb *CircuitBreaker) isClosed() bool {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state == int32(StateClosed)
}

// Open circuit
func (cb *CircuitBreaker) open() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	
	if cb.state != int32(StateOpen) {
		atomic.StoreInt32(&cb.state, int32(StateOpen))
		atomic.StoreInt64(&cb.lastFailureTime, time.Now().Unix())
		atomic.AddInt64(&cb.metrics.CircuitOpensTotal, 1)
		logger.Warnf("Circuit breaker opened due to failure threshold")
	}
}

// Close circuit
func (cb *CircuitBreaker) close() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	
	if cb.state != int32(StateClosed) {
		atomic.StoreInt32(&cb.state, int32(StateClosed))
		atomic.StoreInt64(&cb.failures, 0)
		atomic.AddInt64(&cb.metrics.CircuitClosesTotal, 1)
		logger.Infof("Circuit breaker closed")
	}
}

// Set circuit to half-open
func (cb *CircuitBreaker) halfOpen() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	
	if cb.state != int32(StateHalfOpen) {
		atomic.StoreInt32(&cb.state, int32(StateHalfOpen))
		logger.Infof("Circuit breaker set to half-open state")
	}
}

// Check thresholds and potentially open circuit
func (cb *CircuitBreaker) checkThresholds() {
	failures := atomic.LoadInt64(&cb.failures)
	if failures >= int64(cb.config.MaxFailures) {
		cb.open()
	}
}

// Record request
func (cb *CircuitBreaker) recordRequest() {
	if cb.config.EnableMetrics {
		atomic.AddInt64(&cb.metrics.RequestsTotal, 1)
	}
}

// Record success
func (cb *CircuitBreaker) recordSuccess() {
	if cb.config.EnableMetrics {
		atomic.AddInt64(&cb.metrics.SuccessesTotal, 1)
	}
	
	// Reset failure count on success
	atomic.StoreInt64(&cb.failures, 0)
}

// Record failure
func (cb *CircuitBreaker) recordFailure() {
	if cb.config.EnableMetrics {
		atomic.AddInt64(&cb.metrics.FailuresTotal, 1)
	}
	
	atomic.AddInt64(&cb.failures, 1)
	atomic.StoreInt64(&cb.lastFailureTime, time.Now().Unix())
}

// Record timeout
func (cb *CircuitBreaker) recordTimeout() {
	if cb.config.EnableMetrics {
		atomic.AddInt64(&cb.metrics.TimeoutsTotal, 1)
	}
	
	atomic.AddInt64(&cb.failures, 1)
	atomic.StoreInt64(&cb.lastFailureTime, time.Now().Unix())
}

// Get circuit state
func (cb *CircuitBreaker) GetState() CircuitState {
	return CircuitState(atomic.LoadInt32(&cb.state))
}

// Get metrics
func (cb *CircuitBreaker) GetMetrics() CircuitBreakerMetrics {
	return CircuitBreakerMetrics{
		RequestsTotal:      atomic.LoadInt64(&cb.metrics.RequestsTotal),
		SuccessesTotal:    atomic.LoadInt64(&cb.metrics.SuccessesTotal),
		FailuresTotal:     atomic.LoadInt64(&cb.metrics.FailuresTotal),
		CircuitOpensTotal: atomic.LoadInt64(&cb.metrics.CircuitOpensTotal),
		CircuitClosesTotal: atomic.LoadInt64(&cb.metrics.CircuitClosesTotal),
		TimeoutsTotal:     atomic.LoadInt64(&cb.metrics.TimeoutsTotal),
	}
}

// Reset circuit breaker
func (cb *CircuitBreaker) Reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	
	atomic.StoreInt32(&cb.state, int32(StateClosed))
	atomic.StoreInt64(&cb.failures, 0)
	atomic.StoreInt64(&cb.lastFailureTime, 0)
	atomic.StoreInt64(&cb.generation, atomic.LoadInt64(&cb.generation)+1)
	
	logger.Infof("Circuit breaker reset")
}

// Get circuit breaker generation
func (cb *CircuitBreaker) GetGeneration() int64 {
	return atomic.LoadInt64(&cb.generation)
}

// String representation of circuit state
func (s CircuitState) String() string {
	switch s {
	case StateClosed:
		return "CLOSED"
	case StateOpen:
		return "OPEN"
	case StateHalfOpen:
		return "HALF_OPEN"
	default:
		return "UNKNOWN"
	}
}

// Circuit breaker with exponential backoff retry
type CircuitBreakerWithRetry struct {
	*CircuitBreaker
	retryConfig *RetryConfig
}

// Retry configuration
type RetryConfig struct {
	// Maximum number of retry attempts
	MaxRetries int `json:"max_retries" yaml:"max_retries"`
	
	// Initial backoff delay
	InitialDelay time.Duration `json:"initial_delay" yaml:"initial_delay"`
	
	// Maximum backoff delay
	MaxDelay time.Duration `json:"max_delay" yaml:"max_delay"`
	
	// Backoff multiplier
	Multiplier float64 `json:"multiplier" yaml:"multiplier"`
	
	// Whether to use jitter
	Jitter bool `json:"jitter" yaml:"jitter"`
	
	// Retryable error codes
	RetryableCodes []codes.Code `json:"retryable_codes" yaml:"retryable_codes"`
}

// Default retry configuration
func DefaultRetryConfig() *RetryConfig {
	return &RetryConfig{
		MaxRetries:     3,
		InitialDelay:    100 * time.Millisecond,
		MaxDelay:        5 * time.Second,
		Multiplier:      2.0,
		Jitter:          true,
		RetryableCodes: []codes.Code{
			codes.Unavailable,
			codes.DeadlineExceeded,
			codes.Aborted,
			codes.OutOfRange,
			codes.DataLoss,
			codes.Unauthenticated,
		},
	}
}

// Create circuit breaker with retry
func NewCircuitBreakerWithRetry(cbConfig *CircuitBreakerConfig, retryConfig *RetryConfig) *CircuitBreakerWithRetry {
	if cbConfig == nil {
		cbConfig = DefaultCircuitBreakerConfig()
	}
	if retryConfig == nil {
		retryConfig = DefaultRetryConfig()
	}
	
	return &CircuitBreakerWithRetry{
		CircuitBreaker: NewCircuitBreaker(cbConfig),
		retryConfig:    retryConfig,
	}
}

// Execute with circuit breaker and retry
func (cbr *CircuitBreakerWithRetry) Execute(ctx context.Context, fn func() error) error {
	var lastErr error
	
	for attempt := 0; attempt <= cbr.retryConfig.MaxRetries; attempt++ {
		// Check if context is cancelled
		if ctx.Err() != nil {
			return ctx.Err()
		}
		
		// Execute with circuit breaker
		err := cbr.CircuitBreaker.Execute(ctx, fn)
		if err == nil {
			if attempt > 0 {
				logger.Infof("Request succeeded after %d attempts", attempt+1)
			}
			return nil
		}
		
		lastErr = err
		
		// Check if error is retryable
		if !cbr.isRetryableError(err) {
			logger.Warnf("Non-retryable error: %v", err)
			return err
		}
		
		// Check if this is the last attempt
		if attempt == cbr.retryConfig.MaxRetries {
			logger.Errorf("Max retries (%d) exceeded, last error: %v", cbr.retryConfig.MaxRetries, err)
			return err
		}
		
		// Calculate backoff delay
		delay := cbr.calculateBackoff(attempt)
		logger.Warnf("Request failed (attempt %d/%d): %v, retrying in %v", attempt+1, cbr.retryConfig.MaxRetries, err, delay)
		
		// Wait before retry
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(delay):
			// Continue to next attempt
		}
	}
	
	return lastErr
}

// Check if error is retryable
func (cbr *CircuitBreakerWithRetry) isRetryableError(err error) bool {
	if err == nil {
		return false
	}
	
	// Check gRPC status code
	if grpcErr, ok := err.(interface{ GRPCStatus() (codes.Code) }); ok {
		for _, retryableCode := range cbr.retryConfig.RetryableCodes {
			if grpcErr.GRPCStatus() == retryableCode {
				return true
			}
		}
	}
	
	return false
}

// Calculate exponential backoff delay
func (cbr *CircuitBreakerWithRetry) calculateBackoff(attempt int) time.Duration {
	delay := float64(cbr.retryConfig.InitialDelay) * math.Pow(cbr.retryConfig.Multiplier, float64(attempt))
	
	// Apply maximum delay
	if delay > float64(cbr.retryConfig.MaxDelay) {
		delay = float64(cbr.retryConfig.MaxDelay)
	}
	
	// Add jitter if enabled
	if cbr.retryConfig.Jitter {
		// Add random jitter up to 25% of delay
		jitter := delay * 0.25 * (rand.Float64() - 0.5)
		delay += jitter
	}
	
	return time.Duration(delay)
}

// Get retry configuration
func (cbr *CircuitBreakerWithRetry) GetRetryConfig() *RetryConfig {
	return cbr.retryConfig
}

// Get combined metrics
func (cbr *CircuitBreakerWithRetry) GetMetrics() CircuitBreakerWithRetryMetrics {
	cbMetrics := cbr.CircuitBreaker.GetMetrics()
	
	return CircuitBreakerWithRetryMetrics{
		CircuitBreakerMetrics: cbMetrics,
		MaxRetries:             cbr.retryConfig.MaxRetries,
		CurrentRetry:           0, // This would need to be tracked during execution
		InitialDelay:           cbr.retryConfig.InitialDelay,
		MaxDelay:               cbr.retryConfig.MaxDelay,
		Multiplier:             cbr.retryConfig.Multiplier,
		Jitter:                 cbr.retryConfig.Jitter,
	}
}

// Combined metrics
type CircuitBreakerWithRetryMetrics struct {
	CircuitBreakerMetrics
	MaxRetries     int
	CurrentRetry   int
	InitialDelay   time.Duration
	MaxDelay       time.Duration
	Multiplier     float64
	Jitter         bool
}
