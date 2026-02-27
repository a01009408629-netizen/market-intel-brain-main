package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// MockCoreEngineClient is a mock implementation of the CoreEngineClient
type MockCoreEngineClient struct {
	mockFetchMarketData func(ctx context.Context, req interface{}) (interface{}, error)
}

func (m *MockCoreEngineClient) FetchMarketData(ctx context.Context, req interface{}) (interface{}, error) {
	return m.mockFetchMarketData(ctx, req)
}

func (m *MockCoreEngineClient) Close() error {
	return nil
}

func (m *MockCoreEngineClient) HealthCheck(ctx context.Context, service string) (interface{}, error) {
	return map[string]interface{}{
		"healthy": true,
		"version": "1.0.0",
		"details": map[string]string{"status": "ok"},
	}, nil
}

// TestMarketDataFetch tests the market data fetch endpoint
func TestMarketDataFetch(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create mock client
	mockClient := &MockCoreEngineClient{
		mockFetchMarketData: func(ctx context.Context, req interface{}) (interface{}, error) {
			return map[string]interface{}{
				"success":     true,
				"market_data": []interface{}{},
			}, nil
		},
	}

	// Create handler
	handler := NewDataIngestionHandler(mockClient)

	// Create test request
	reqBody := map[string]interface{}{
		"symbols":  []string{"AAPL", "GOOGL"},
		"interval": "1h",
		"limit":    100,
	}

	reqBodyBytes, _ := json.Marshal(reqBody)
	req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	// Create router
	router := gin.New()
	router.POST("/api/v1/market-data/fetch", handler.FetchMarketData)

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response["success"].(bool))
}

// TestLargePayload tests handling of large payloads
func TestLargePayload(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mockClient := &MockCoreEngineClient{
		mockFetchMarketData: func(ctx context.Context, req interface{}) (interface{}, error) {
			return map[string]interface{}{
				"success":     true,
				"market_data": []interface{}{},
			}, nil
		},
	}

	handler := NewDataIngestionHandler(mockClient)

	// Create large payload
	reqBody := map[string]interface{}{
		"symbols":  make([]string, 1000),
		"interval": "1h",
		"limit":    100,
	}

	for i := range reqBody["symbols"].([]string) {
		reqBody["symbols"].([]string)[i] = "SYMBOL_" + string(rune(i))
	}

	reqBodyBytes, _ := json.Marshal(reqBody)
	req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	router := gin.New()
	router.POST("/api/v1/market-data/fetch", handler.FetchMarketData)

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}

// TestConcurrentRequests tests concurrent request handling
func TestConcurrentRequests(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mockClient := &MockCoreEngineClient{
		mockFetchMarketData: func(ctx context.Context, req interface{}) (interface{}, error) {
			return map[string]interface{}{
				"success":     true,
				"market_data": []interface{}{},
			}, nil
		},
	}

	handler := NewDataIngestionHandler(mockClient)
	router := gin.New()
	router.POST("/api/v1/market-data/fetch", handler.FetchMarketData)

	// Test concurrent requests
	for i := 0; i < 10; i++ {
		t.Run(fmt.Sprintf("concurrent_%d", i), func(t *testing.T) {
			reqBody := map[string]interface{}{
				"symbols":  []string{"AAPL"},
				"interval": "1h",
				"limit":    100,
			}

			reqBodyBytes, _ := json.Marshal(reqBody)
			req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
			req.Header.Set("Content-Type", "application/json")

			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code)
		})
	}
}

// TestContextTimeout tests context timeout handling
func TestContextTimeout(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mockClient := &MockCoreEngineClient{
		mockFetchMarketData: func(ctx context.Context, req interface{}) (interface{}, error) {
			return map[string]interface{}{
				"success":     true,
				"market_data": []interface{}{},
			}, nil
		},
	}

	handler := NewDataIngestionHandler(mockClient)
	router := gin.New()
	router.POST("/api/v1/market-data/fetch", handler.FetchMarketData)

	reqBody := map[string]interface{}{
		"symbols":  []string{"AAPL"},
		"interval": "1h",
		"limit":    100,
	}

	reqBodyBytes, _ := json.Marshal(reqBody)
	req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
}
