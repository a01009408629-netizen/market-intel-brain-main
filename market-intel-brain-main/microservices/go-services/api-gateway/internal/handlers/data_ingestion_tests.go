package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"

	"github.com/market-intel/api-gateway/internal/config"
	pb "github.com/market-intel/api-gateway/pb"
)

// MockCoreEngineClient is a mock implementation of CoreEngineInterface
type MockCoreEngineClient struct {
	mockFetchMarketData      func(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error)
	mockFetchNewsData        func(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error)
	mockConnectDataSource     func(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error)
	mockGetMarketDataBuffer func(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error)
	mockGetNewsBuffer        func(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error)
	mockGetIngestionStats   func(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error)
}

func (m *MockCoreEngineClient) FetchMarketData(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
	return m.mockFetchMarketData(ctx, req)
}

func (m *MockCoreEngineClient) FetchNewsData(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
	return m.mockFetchNewsData(ctx, req)
}

func (m *MockCoreEngineClient) ConnectDataSource(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
	return m.mockConnectDataSource(ctx, req)
}

func (m *MockCoreEngineClient) GetMarketDataBuffer(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
	return m.mockGetMarketDataBuffer(ctx, req)
}

func (m *MockCoreEngineClient) GetNewsBuffer(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
	return m.mockGetNewsBuffer(ctx, req)
}

func (m *MockCoreEngineClient) GetIngestionStats(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
	return m.mockGetIngestionStats(ctx, req)
}

func (m *MockCoreEngineClient) HealthCheck(ctx context.Context, service string) error {
	return nil
}

func (m *MockCoreEngineClient) ExecuteWithCircuitBreaker(ctx context.Context, operation func() error) error {
	return operation()
}

func (m *MockCoreEngineClient) Close() error {
	return nil
}

// TestMarketDataFetch tests the market data fetch endpoint
func TestMarketDataFetch(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create mock client
	mockClient := &MockCoreEngineClient{
		mockFetchMarketData: func(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
			return &pb.FetchMarketDataResponse{
				Success:     true,
				MarketData: []pb.MarketData{},
			}, nil
		},
		mockGetMarketDataBuffer: func(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
			return &pb.GetMarketDataBufferResponse{
				Success:     true,
				MarketData: []pb.MarketData{},
			}, nil
		},
		mockGetNewsBuffer: func(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
			return &pb.GetNewsBufferResponse{
				Success:   true,
				NewsData: []pb.NewsData{},
			}, nil
		},
		mockGetIngestionStats: func(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
			return &pb.GetIngestionStatsResponse{
				Success: true,
				Stats:   map[string]interface{}{},
			}, nil
		},
	}

	// Create test config
	cfg := &config.Config{
		Environment: "test",
	}

	// Create handler
	handler := NewDataIngestionHandler(cfg, mockClient)

	// Create test request
	reqBody := map[string]interface{}{
		"symbols":  []string{"AAPL", "GOOGL"},
		"interval": "1h",
		"limit":    100,
	}

	jsonBody, _ := json.Marshal(reqBody)

	// Create HTTP request
	httpReq, _ := http.NewRequest("POST", "/api/v1/market/data", bytes.NewBuffer(jsonBody))
	httpReq.Header.Set("Content-Type", "application/json")

	// Create response recorder
	w := httptest.NewRecorder()

	// Create Gin context and handle request
	c, _ := gin.CreateTestContext(w)
	handler.FetchMarketData(c)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.True(t, response["success"].(bool))
}

// TestNewsDataFetch tests the news data fetch endpoint
func TestNewsDataFetch(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create mock client
	mockClient := &MockCoreEngineClient{
		mockFetchNewsData: func(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
			return &pb.FetchNewsDataResponse{
				Success:     true,
				NewsData: []pb.NewsData{},
			}, nil
		},
		mockGetMarketDataBuffer: func(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
			return &pb.GetMarketDataBufferResponse{
				Success:     true,
				MarketData: []pb.MarketData{},
			}, nil
		},
		mockGetNewsBuffer: func(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
			return &pb.GetNewsBufferResponse{
				Success:   true,
				NewsData: []pb.NewsData{},
			}, nil
		},
		mockGetIngestionStats: func(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
			return &pb.GetIngestionStatsResponse{
				Success: true,
				Stats:   map[string]interface{}{},
			}, nil
		},
	}

	// Create test config
	cfg := &config.Config{
		Environment: "test",
	}

	// Create handler
	handler := NewDataIngestionHandler(cfg, mockClient)

	// Create test request
	reqBody := map[string]interface{}{
		"source_id": "reuters",
		"limit":     50,
	}

	jsonBody, _ := json.Marshal(reqBody)

	// Create HTTP request
	httpReq, _ := http.NewRequest("POST", "/api/v1/news/data", bytes.NewBuffer(jsonBody))
	httpReq.Header.Set("Content-Type", "application/json")

	// Create response recorder
	w := httptest.NewRecorder()

	// Create Gin context and handle request
	c, _ := gin.CreateTestContext(w)
	handler.FetchNewsData(c)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.True(t, response["success"].(bool))
}

// TestConnectDataSource tests the data source connection endpoint
func TestConnectDataSource(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create mock client
	mockClient := &MockCoreEngineClient{
		mockConnectDataSource: func(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
			return &pb.ConnectDataSourceResponse{
				Success: true,
				Message: "Data source connected successfully",
			}, nil
		},
		mockGetMarketDataBuffer: func(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
			return &pb.GetMarketDataBufferResponse{
				Success:     true,
				MarketData: []pb.MarketData{},
			}, nil
		},
		mockGetNewsBuffer: func(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
			return &pb.GetNewsBufferResponse{
				Success:   true,
				NewsData: []pb.NewsData{},
			}, nil
		},
		mockGetIngestionStats: func(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
			return &pb.GetIngestionStatsResponse{
				Success: true,
				Stats:   map[string]interface{}{},
			}, nil
		},
	}

	// Create test config
	cfg := &config.Config{
		Environment: "test",
	}

	// Create handler
	handler := NewDataIngestionHandler(cfg, mockClient)

	// Create test request
	reqBody := map[string]interface{}{
		"source_id": "alpha_vantage",
		"config": map[string]interface{}{
			"api_key": "test_key",
			"timeout": 30,
		},
	}

	jsonBody, _ := json.Marshal(reqBody)

	// Create HTTP request
	httpReq, _ := http.NewRequest("POST", "/api/v1/data-sources/connect", bytes.NewBuffer(jsonBody))
	httpReq.Header.Set("Content-Type", "application/json")

	// Create response recorder
	w := httptest.NewRecorder()

	// Create Gin context and handle request
	c, _ := gin.CreateTestContext(w)
	handler.ConnectDataSource(c)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.True(t, response["success"].(bool))
}

// TestHealthCheck tests the health check endpoint
func TestHealthCheck(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Create mock client
	mockClient := &MockCoreEngineClient{
		mockGetMarketDataBuffer: func(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
			return &pb.GetMarketDataBufferResponse{
				Success:     true,
				MarketData: []pb.MarketData{},
			}, nil
		},
		mockGetNewsBuffer: func(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
			return &pb.GetNewsBufferResponse{
				Success:   true,
				NewsData: []pb.NewsData{},
			}, nil
		},
		mockGetIngestionStats: func(ctx context.Context, req *pb.GetIngestionStatsRequest) (*pb.GetIngestionStatsResponse, error) {
			return &pb.GetIngestionStatsResponse{
				Success: true,
				Stats:   map[string]interface{}{},
			}, nil
		},
	}

	// Create test config
	cfg := &config.Config{
		Environment: "test",
	}

	// Create handler
	handler := NewDataIngestionHandler(cfg, mockClient)

	// Create HTTP request
	healthReq, _ := http.NewRequest("GET", "/api/v1/health?service=api-gateway", nil)

	// Create response recorder
	w := httptest.NewRecorder()

	// Create Gin context and handle request
	c, _ := gin.CreateTestContext(w)
	_ = healthReq  // Use the variable to avoid unused error
	handler.HealthCheck(c)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.True(t, response["success"].(bool))
}
