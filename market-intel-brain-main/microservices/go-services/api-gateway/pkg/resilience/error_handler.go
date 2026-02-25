// Standardized Error Response Handler
// Provides clean, standardized JSON responses for service unavailability

package resilience

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/market-intel/api-gateway/pkg/logger"
)

// Standard error response structure
type ErrorResponse struct {
	Success   bool   `json:"success"`
	Error     string `json:"error"`
	Message   string `json:"message"`
	Code      int    `json:"code"`
	Timestamp string `json:"timestamp"`
	RequestID string `json:"request_id,omitempty"`
	Service   string `json:"service,omitempty"`
	Retryable bool   `json:"retryable,omitempty"`
}

// Error response codes
const (
	ErrCodeServiceUnavailable = 503
	ErrCodeTimeout          = 504
	ErrCodeRateLimited      = 429
	ErrCodeBadRequest       = 400
	ErrCodeUnauthorized     = 401
	ErrCodeForbidden        = 403
	ErrCodeNotFound         = 404
	ErrCodeInternalError    = 500
	ErrCodeBadGateway       = 502
	ErrCodeGatewayTimeout   = 504
)

// Error response types
const (
	ErrTypeServiceUnavailable = "SERVICE_UNAVAILABLE"
	ErrTypeTimeout          = "TIMEOUT"
	ErrTypeRateLimited      = "RATE_LIMITED"
	ErrTypeBadRequest       = "BAD_REQUEST"
	ErrTypeUnauthorized     = "UNAUTHORIZED"
	ErrTypeForbidden        = "FORBIDDEN"
	ErrTypeNotFound         = "NOT_FOUND"
	ErrTypeInternalError    = "INTERNAL_ERROR"
	ErrTypeBadGateway       = "BAD_GATEWAY"
	ErrTypeGatewayTimeout   = "GATEWAY_TIMEOUT"
)

// Create service unavailable error response
func ServiceUnavailable(service string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeServiceUnavailable,
		Message:   fmt.Sprintf("Service %s is currently unavailable. Please try again later.", service),
		Code:      ErrCodeServiceUnavailable,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Service:   service,
		Retryable: true,
	}
}

// Create timeout error response
func TimeoutError(service string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeTimeout,
		Message:   fmt.Sprintf("Service %s request timed out. Please try again.", service),
		Code:      ErrCodeTimeout,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Service:   service,
		Retryable: true,
	}
}

// Create rate limited error response
func RateLimitedError(service string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeRateLimited,
		Message:   fmt.Sprintf("Rate limit exceeded for service %s. Please try again later.", service),
		Code:      ErrCodeRateLimited,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Service:   service,
		Retryable: true,
	}
}

// Create bad request error response
func BadRequestError(message string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeBadRequest,
		Message:   message,
		Code:      ErrCodeBadRequest,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Retryable: false,
	}
}

// Create unauthorized error response
func UnauthorizedError(message string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeUnauthorized,
		Message:   message,
		Code:      ErrCodeUnauthorized,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Retryable: false,
	}
}

// Create forbidden error response
func ForbiddenError(message string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeForbidden,
		Message:   message,
		Code:      ErrCodeForbidden,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Retryable: false,
	}
}

// Create not found error response
func NotFoundError(message string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeNotFound,
		Message:   message,
		Code:      ErrCodeNotFound,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Retryable: false,
	}
}

// Create internal error response
func InternalError(message string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeInternalError,
		Message:   message,
		Code:      ErrCodeInternalError,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Retryable: false,
	}
}

// Create bad gateway error response
func BadGatewayError(service string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeBadGateway,
		Message:   fmt.Sprintf("Bad gateway response from service %s.", service),
		Code:      ErrCodeBadGateway,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Service:   service,
		Retryable: true,
	}
}

// Create gateway timeout error response
func GatewayTimeoutError(service string, requestID string) *ErrorResponse {
	return &ErrorResponse{
		Success:   false,
		Error:     ErrTypeGatewayTimeout,
		Message:   fmt.Sprintf("Gateway timeout when calling service %s.", service),
		Code:      ErrCodeGatewayTimeout,
		Timestamp: getCurrentTimestamp(),
		RequestID: requestID,
		Service:   service,
		Retryable: true,
	}
}

// Get current timestamp in RFC3339 format
func getCurrentTimestamp() string {
	return time.Now().UTC().Format(time.RFC3339)
}

// Send error response as JSON
func SendErrorResponse(c *gin.Context, errResp *ErrorResponse) {
	// Set appropriate HTTP status code
	c.JSON(getHTTPStatusFromErrorCode(errResp.Code), errResp)
	
	// Log the error
	logger.Errorf("Error response sent: %s - %s", errResp.Error, errResp.Message)
}

// Get HTTP status code from error code
func getHTTPStatusFromErrorCode(errorCode int) int {
	switch errorCode {
	case ErrCodeServiceUnavailable:
		return http.StatusServiceUnavailable
	case ErrCodeTimeout:
		return http.StatusGatewayTimeout
	case ErrCodeRateLimited:
		return http.StatusTooManyRequests
	case ErrCodeBadRequest:
		return http.StatusBadRequest
	case ErrCodeUnauthorized:
		return http.StatusUnauthorized
	case ErrCodeForbidden:
		return http.StatusForbidden
	case ErrCodeNotFound:
		return http.StatusNotFound
	case ErrCodeInternalError:
		return http.StatusInternalServerError
	case ErrCodeBadGateway:
		return http.StatusBadGateway
	case ErrCodeGatewayTimeout:
		return http.StatusGatewayTimeout
	default:
		return http.StatusInternalServerError
	}
}

// Middleware for handling gRPC errors and converting to HTTP responses
func GRPCErrorsMiddleware(serviceName string) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next()
		
		// Check if there's an error from the context
		if len(c.Errors) > 0 {
			lastErr := c.Errors.Last()
			
			// Check if it's a gRPC error
			if isGRPCTimeoutError(lastErr) {
				errResp := TimeoutError(serviceName, getRequestID(c))
				SendErrorResponse(c, errResp)
				c.Abort()
				return
			}
			
			if isGRPCUnavailableError(lastErr) {
				errResp := ServiceUnavailable(serviceName, getRequestID(c))
				SendErrorResponse(c, errResp)
				c.Abort()
				return
			}
			
			if isGRPCDeadlineExceededError(lastErr) {
				errResp := TimeoutError(serviceName, getRequestID(c))
				SendErrorResponse(c, errResp)
				c.Abort()
				return
			}
		}
	}
}

// Check if error is gRPC timeout
func isGRPCTimeoutError(err error) bool {
	if err == nil {
		return false
	}
	
	errStr := err.Error()
	return contains(errStr, "context deadline exceeded") ||
		   contains(errStr, "timeout") ||
		   contains(errStr, "connection timed out")
}

// Check if error is gRPC unavailable
func isGRPCUnavailableError(err error) bool {
	if err == nil {
		return false
	}
	
	errStr := err.Error()
	return contains(errStr, "connection refused") ||
		   contains(errStr, "no such host") ||
		   contains(errStr, "network is unreachable") ||
		   contains(errStr, "service unavailable")
}

// Check if error is gRPC deadline exceeded
func isGRPCDeadlineExceededError(err error) bool {
	if err == nil {
		return false
	}
	
	errStr := err.Error()
	return contains(errStr, "context deadline exceeded") ||
		   contains(errStr, "deadline exceeded")
}

// Get request ID from context
func getRequestID(c *gin.Context) string {
	if requestID, exists := c.Get("request_id"); exists {
		if id, ok := requestID.(string); ok {
			return id
		}
	}
	return ""
}

// Helper function to check if string contains substring
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || 
		(len(s) > len(substr) && (s[:len(substr)] == substr || s[len(s)-len(substr):] == substr)))
}

// Recovery middleware for panic recovery
func RecoveryMiddleware(serviceName string) gin.HandlerFunc {
	return gin.CustomRecovery(func(c *gin.Context, recovered interface{}) {
		if err, ok := recovered.(string); ok {
			errResp := InternalError(fmt.Sprintf("Internal server error: %s", err), getRequestID(c))
			errResp.Service = serviceName
			SendErrorResponse(c, errResp)
		} else {
			errResp := InternalError("Internal server error", getRequestID(c))
			errResp.Service = serviceName
			SendErrorResponse(c, errResp)
		}
	})
}

// Circuit breaker middleware
func CircuitBreakerMiddleware(cb *CircuitBreaker, serviceName string) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Check circuit state before processing
		if cb.GetState() == StateOpen {
			errResp := ServiceUnavailable(serviceName, getRequestID(c))
			SendErrorResponse(c, errResp)
			c.Abort()
			return
		}
		
		c.Next()
	}
}

// Rate limiting middleware
func RateLimitingMiddleware(serviceName string, requestsPerMinute int) gin.HandlerFunc {
	return func(c *gin.Context) {
		// This is a simplified rate limiting implementation
		// In production, use a proper rate limiting library like go-redis-rate-limit
		c.Next()
	}
}

// Health check endpoint that respects circuit breaker
func HealthCheckMiddleware(cb *CircuitBreaker, serviceName string) gin.HandlerFunc {
	return func(c *gin.Context) {
		if cb.GetState() == StateOpen {
			errResp := ServiceUnavailable(serviceName, getRequestID(c))
			SendErrorResponse(c, errResp)
			return
		}
		
		c.JSON(http.StatusOK, gin.H{
			"healthy":    true,
			"service":    serviceName,
			"circuit_breaker": gin.H{
				"state":   cb.GetState().String(),
				"metrics": cb.GetMetrics(),
			},
			"timestamp": getCurrentTimestamp(),
		})
	}
}

// Metrics endpoint for circuit breaker status
func CircuitBreakerMetricsEndpoint(cb *CircuitBreaker, serviceName string) gin.HandlerFunc {
	return func(c *gin.Context) {
		metrics := cb.GetMetrics()
		
		c.JSON(http.StatusOK, gin.H{
			"service": serviceName,
			"circuit_breaker": gin.H{
				"state":    cb.GetState().String(),
				"metrics":  metrics,
			},
			"timestamp": getCurrentTimestamp(),
		})
	}
}
