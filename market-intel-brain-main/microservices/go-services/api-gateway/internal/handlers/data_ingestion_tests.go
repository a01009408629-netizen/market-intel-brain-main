package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang/protobuf/ptypes"
	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/pkg/logger"
	pb "github.com/market-intel/api-gateway/proto"
)

// MockCoreEngineClient is a mock implementation of the CoreEngineClient
type MockCoreEngineClient struct {
	mockFetchMarketData func(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error)
	mockFetchNewsData    func(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error)
	mockGetMarketDataBuffer func(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error)
	mockGetNewsBuffer    func(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error)
	mockGetIngestionStats func(ctx context.Context, req *pb.Empty) (*pb.GetIngestionStatsResponse, error)
	mockConnectDataSource func(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error)
}

func (m *MockCoreEngineClient) FetchMarketData(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
	return m.mockFetchMarketData(ctx, req)
}

func (m *MockCoreEngineClient) FetchNewsData(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
	return m.mockFetchNewsData(ctx, req)
}

func (m *MockCoreEngineClient) GetMarketDataBuffer(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
	return m.mockGetMarketDataBuffer(ctx, req)
}

func (m *MockCoreEngineClient) GetNewsBuffer(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
	return m.mockGetNewsBuffer(ctx, req)
}

func (m *MockCoreEngineClient) GetIngestionStats(ctx context.Context, req *pb.Empty) (*pb.GetIngestionStatsResponse, error) {
	return m.mockGetIngestionStats(ctx, req)
}

func (m *MockCoreEngineClient) ConnectDataSource(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
	return m.mockConnectDataSource(ctx, req)
}

func (m *MockCoreEngineClient) Close() error {
	return nil
}

func (m *MockCoreEngineClient) HealthCheck(ctx context.Context, serviceName string) (*pb.HealthCheckResponse, error) {
	return &pb.HealthCheckResponse{
		Healthy: true,
		Status:  "healthy",
		Version: "1.0.0",
	}, nil
}

func (m *MockCoreEngineClient) GetStatus(ctx context.Context) (*pb.EngineStatusResponse, error) {
	return &pb.EngineStatusResponse{
		Status: pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
		Message: "Engine is running",
	}, nil
}

func setupTestRouter() (*gin.Engine, *MockCoreEngineClient) {
	// Initialize logger
	logger.Init()

	// Create timestamp for mock data
	timestamp, _ := ptypes.TimestampProto(time.Date(2022, 1, 1, 0, 0, 0, 0, time.UTC))

	// Create mock client
	mockClient := &MockCoreEngineClient{
		mockFetchMarketData: func(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
			return &pb.FetchMarketDataResponse{
				Status:     pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
				Message:    "Mock market data fetched",
				MarketData: []pb.MarketData{
					{
						Symbol:    "AAPL",
						Price:     150.25,
						Volume:    1000000,
						Timestamp: timestamp,
						Source:    "yahoo_finance",
						AdditionalData: map[string]string{
							"currency": "USD",
							"market":  "NASDAQ",
						},
					},
				},
			}, nil
		},
		mockFetchNewsData: func(ctx context.Context, req *pb.FetchNewsDataRequest) (*pb.FetchNewsDataResponse, error) {
			return &pb.FetchNewsDataResponse{
				Status:    pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
				Message:  "Mock news data fetched",
				NewsItems: []pb.NewsItem{
					{
						Title:     "Stock Market Rally",
						Content:   "Technology stocks surge",
						Source:    "Reuters",
						Timestamp: timestamp,
						SentimentScore: 0.8,
						RelevanceScore: 0.9,
					},
				},
			}, nil
		},
		mockGetMarketDataBuffer: func(ctx context.Context, req *pb.GetMarketDataBufferRequest) (*pb.GetMarketDataBufferResponse, error) {
			return &pb.GetMarketDataBufferResponse{
				Status:     pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
				Message:    "Mock market data buffer retrieved",
				MarketData: []pb.MarketData{
					{
						Symbol:    "AAPL",
						Price:     150.25,
						Volume:    1000000,
						Timestamp: timestamp,
						Source:    "yahoo_finance",
						AdditionalData: map[string]string{
							"currency": "USD",
							"market":  "NASDAQ",
						},
					},
				},
			}, nil
		},
		mockGetNewsBuffer: func(ctx context.Context, req *pb.GetNewsBufferRequest) (*pb.GetNewsBufferResponse, error) {
			return &pb.GetNewsBufferResponse{
				Status:   pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
				Message: "Mock news buffer retrieved",
				NewsItems: []pb.NewsItem{
					{
						Title:     "Stock Market Rally",
						Content:   "Technology stocks surge",
						Source:    "Reuters",
						Timestamp: timestamp,
						SentimentScore: 0.8,
						RelevanceScore: 0.9,
					},
				},
			}, nil
		},
		mockGetIngestionStats: func(ctx context.Context, req *pb.Empty) (*pb.GetIngestionStatsResponse, error) {
			return &pb.GetIngestionStatsResponse{
				Status: pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
				Message: "Mock ingestion stats retrieved",
				Stats: &pb.IngestionStats{
					ActiveConnections:      2,
					ConfiguredSources:      4,
					MarketDataBufferSize:   500,
					NewsBufferSize:          250,
					MaxBufferSize:          1000,
					DataSources: map[string]*pb.DataSourceInfo{
						"yahoo_finance": {
							Type:     "market_data",
							Enabled:  true,
							Connected: true,
						},
						"news_api": {
							Type:     "news",
							Enabled:  false,
							Connected: false,
						},
					},
				},
			}, nil
		},
		mockConnectDataSource: func(ctx context.Context, req *pb.ConnectDataSourceRequest) (*pb.ConnectDataSourceResponse, error) {
			return &pb.ConnectDataSourceResponse{
				Status:    pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
				Message:   "Mock connection successful",
				Connected: true,
			}, nil
		},
	}

	config := &config.Config{
		HTTPPort:       8080,
		GRPCPort:       8081,
		DatabaseURL:    "postgres://postgres:postgres@localhost:5432/market_intel",
		RedisURL:       "redis://localhost:6379",
		RedpandaBrokers: "localhost:9092",
		CoreEngineURL: "localhost:50052",
		AuthServiceURL: "localhost:50051",
		LogLevel:       "info",
		Environment:    "test",
	}

	handler := NewDataIngestionHandler(config, mockClient)
	router := gin.New()
	
	// Setup routes
	v1 := router.Group("/api/v1")
	{
		v1.POST("/market-data/fetch", handler.FetchMarketData)
		v1.POST("/news/fetch", handler.FetchNewsData)
		v1.GET("/market-data/buffer", handler.GetMarketDataBuffer)
		v1.GET("/news/buffer", handler.GetNewsBuffer)
		v1.GET("/ingestion/stats", handler.GetIngestionStats)
		v1.POST("/data-sources/connect", handler.ConnectDataSource)
	}

	return router, mockClient
}

func TestFetchMarketData(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test successful request
	reqBody := FetchMarketDataRequest{
		Symbols:  []string{"AAPL", "GOOGL", "MSFT"},
		SourceID: "yahoo_finance",
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	require.NoError(t, err)

	req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response FetchMarketDataResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response.Success)
	assert.Equal(t, "Mock market data fetched", response.Message)
	assert.Equal(t, 3, len(response.MarketData))
	assert.Equal(t, "AAPL", response.MarketData[0].Symbol)
	assert.Equal(t, 150.25, response.MarketData[0].Price)
	assert.Equal(t, int64(1000000), response.MarketData[0].Volume)
}

func TestFetchMarketDataInvalidRequest(t *testing.T) {
	router, _ := setupTestRouter()

	// Test empty symbols
	reqBody := FetchMarketDataRequest{
		Symbols:  []string{},
		SourceID: "yahoo_finance",
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	require.NoError(t, err)

	req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)

	var response FetchMarketDataResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.False(t, response.Success)
	assert.Contains(t, response.Message, "At least one symbol is required")
}

func TestFetchNewsData(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test successful request
	reqBody := FetchNewsDataRequest{
		Keywords:  []string{"stock", "market", "trading"},
		SourceID: "news_api",
		HoursBack: 24,
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	require.NoError(t, err)

	req, _ := http.NewRequest("POST", "/api/v1/news/fetch", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response FetchNewsDataResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response.Success)
	assert.Equal(t, "Mock news data fetched", response.Message)
	assert.Equal(t, 1, len(response.NewsItems))
	assert.Equal(t, "Stock Market Rally", response.NewsItems[0].Title)
	assert.Equal(t, 0.8, response.NewsItems[0].SentimentScore)
}

func TestGetMarketDataBuffer(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test with symbol filter
	req, _ := http.NewRequest("GET", "/api/v1/market-data/buffer?symbol=AAPL&limit=10", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response GetMarketDataBufferResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response.Success)
	assert.Equal(t, "Mock market data buffer retrieved", response.Message)
	assert.Equal(t, 1, len(response.MarketData))
	assert.Equal(t, "AAPL", response.MarketData[0].Symbol)
}

func TestGetNewsBuffer(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test with keywords filter
	req, _ := http.NewRequest("GET", "/api/v1/news/buffer?keywords=stock&limit=10", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response GetNewsBufferResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response.Success)
	assert.Equal(t, "Mock news buffer retrieved", response.Message)
	assert.Equal(t, 1, len(response.NewsItems))
	assert.Equal(t, "Stock Market Rally", response.NewsItems[0].Title)
}

func TestGetIngestionStats(t *testing.T) {
	router, mockClient := setupTestRouter()

	req, _ := http.NewRequest("GET", "/api/v1/ingestion/stats", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response GetIngestionStatsResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response.Success)
	assert.Equal(t, "Mock ingestion stats retrieved", response.Message)
	assert.NotNil(t, response.Stats)
	assert.Equal(t, 2, response.Stats.ActiveConnections)
	assert.Equal(t, 4, response.Stats.ConfiguredSources)
	assert.Equal(t, 500, response.Stats.MarketDataBufferSize)
	assert.Equal(t, 250, response.Stats.NewsBufferSize)
	assert.Equal(t, 1000, response.Stats.MaxBufferSize)
}

func TestConnectDataSource(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test successful connection
	reqBody := ConnectDataSourceRequest{
		SourceID: "yahoo_finance",
		APIKey:   "",
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	require.NoError(t, err)

	req, _ := http.NewRequest("POST", "/api/v1/data-sources/connect", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response ConnectDataSourceResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response.Success)
	assert.Equal(t, "Mock connection successful", response.Message)
	assert.True(t, response.Connected)
}

func TestConnectDataSourceInvalidRequest(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test empty source ID
	reqBody := ConnectDataSourceRequest{
		SourceID: "",
		APIKey:   "",
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	require.NoError(t, err)

	req, _ := http.NewRequest("POST", "/api/v1/data-sources/connect", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)

	var response ConnectDataSourceResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.False(t, response.Success)
	assert.Contains(t, response.Message, "Source ID is required")
}

func TestGRPCToHTTPErrorMapping(t *testing.T) {
	handler := NewDataIngestionHandler(&config.Config{}, nil)

	// Test various gRPC error codes
	testCases := []struct {
		name           string
		err            error
		expectedStatus int
		expectedMessage string
	}{
		{
			name:           "InvalidArgument",
			err:            status.Error(codes.InvalidArgument, "Invalid symbol"),
			expectedStatus: http.StatusBadRequest,
			expectedMessage: "Invalid symbol",
		},
		{
			name:           "NotFound",
			err:            status.Error(codes.NotFound, "Data source not found"),
			expectedStatus: http.StatusNotFound,
			expectedMessage: "Data source not found",
		},
		{
			name:           "PermissionDenied",
			err:            status.Error(codes.PermissionDenied, "Access denied"),
			expectedStatus: http.StatusForbidden,
			expectedMessage: "Access denied",
		},
		{
			name:           "Unauthenticated",
			err:            status.Error(codes.Unauthenticated, "Authentication required"),
			expectedStatus: http.StatusUnauthorized,
			expectedMessage: "Authentication required",
		},
		{
			name:           "DeadlineExceeded",
			err:            status.Error(codes.DeadlineExceeded, "Request timeout"),
			expectedStatus: http.StatusRequestTimeout,
			expectedMessage: "Request timeout",
		},
		{
			name:           "ResourceExhausted",
			err:            status.Error(codes.ResourceExhausted, "Too many requests"),
			expectedStatus: http.StatusTooManyRequests,
			expectedMessage: "Too many requests",
		},
		{
			name:           "Unavailable",
			err:            status.Error(codes.Unavailable, "Service unavailable"),
			expectedStatus: http.StatusServiceUnavailable,
			expectedMessage: "Service unavailable",
		},
		{
			name:           "Internal",
			err:            status.Error(codes.Internal, "Internal error"),
			expectedStatus: http.StatusInternalServerError,
			expectedMessage: "Internal error",
		},
	}

	for _, tc := range testCases {
		status, message := handler.mapGRPCToHTTPError(tc.err)
		assert.Equal(t, tc.expectedStatus, status, tc.name+": status code mismatch")
		assert.Equal(t, tc.expectedMessage, message, tc.name+": message mismatch")
	}
}

func TestResponseStatusMapping(t *testing.T) {
	handler := NewDataIngestionHandler(&config.Config{}, nil)

	testCases := []struct {
		name     string
		status   pb.ResponseStatus
		expectedStatus int
		expectedMessage string
	}{
		{
			name:     "Success",
			status:   pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
			expectedStatus: http.StatusOK,
			expectedMessage: "Success",
		},
		{
			name:     "Error",
			status:   pb.ResponseStatus_RESPONSE_STATUS_ERROR,
			expectedStatus: http.StatusInternalServerError,
			expectedMessage: "Internal server error",
		},
		{
			name:     "NotFound",
			status:   pb.ResponseStatus_RESPONSE_STATUS_NOT_FOUND,
			expectedStatus: http.StatusNotFound,
			expectedMessage: "Not found",
		},
		{
			name:     "Unauthorized",
			status:   pb.ResponseStatus_RESPONSE_STATUS_UNAUTHORIZED,
			expectedStatus: http.StatusUnauthorized,
			expectedMessage: "Unauthorized",
		},
		{
			name:     "Forbidden",
			status:   pb.ResponseStatus_RESPONSE_STATUS_FORBIDDEN,
			expectedStatus: http.StatusForbidden,
			expectedMessage: "Forbidden",
		},
		{
			name:     "ValidationError",
			status:   pb.ResponseStatus_RESPONSE_STATUS_VALIDATION_ERROR,
			expectedStatus: http.StatusBadRequest,
			expectedMessage: "Validation error",
		},
		{
			name:     "InternalError",
			status:   pb.ResponseStatus_RESPONSE_STATUS_INTERNAL_ERROR,
			expectedStatus: http.StatusInternalServerError,
			expectedMessage: "Internal error",
		},
	}

	for _, tc := range testCases {
		status, message := handler.mapResponseStatus(tc.status)
		assert.Equal(t, tc.expectedStatus, status, tc.name+": status code mismatch")
		assert.Equal(t, tc.expectedMessage, message, tc.name+": message mismatch")
	}
}

func TestWebSocketMarketData(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Create a test WebSocket server
	server := httptest.NewServer(router)
	defer server.Close()

	// Convert http.Handler to http.HandlerFunc
	handler := server.Config.Handler

	// Simulate WebSocket upgrade
	ws := []websocket.Conn{{
		// Mock WebSocket connection
		// In a real test, you would need to implement a proper WebSocket test
	}

	// For now, just test the endpoint exists
	req, _ := http.NewRequest("GET", "/api/v1/ws/market-data", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	// WebSocket upgrade should be attempted
	assert.Equal(t, http.StatusSwitchingProtocols, w.Code)
}

func TestContextTimeout(t *testing.T) {
	// Test that context timeout is properly handled
	mockClient := &MockCoreEngineClient{
		mockFetchMarketData: func(ctx context.Context, req *pb.FetchMarketDataRequest) (*pb.FetchMarketDataResponse, error) {
			// Simulate timeout
			<-ctx.Done()
			return nil, context.DeadlineExceeded
		},
	}

	config := &config.Config{
		HTTPPort: 8080,
		Environment: "test",
	}

	handler := NewDataIngestionHandler(config, mockClient)
	router := gin.New()
	router.POST("/api/v1/market-data/fetch", handler.FetchMarketData)

	// Create request with timeout context
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Millisecond)
	defer cancel()

	reqBody := FetchMarketDataRequest{
		Symbols:  []string{"AAPL"},
		SourceID: "yahoo_finance",
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	require.NoError(t, err)

	// Create gin context with timeout
	c, _ := gin.CreateTestContext(ctx)
	c.Request, _ = http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
	c.Request.Header.Set("Content-Type", "application/json")

	// This should timeout and return an error
	w := httptest.NewRecorder()
	router.ServeHTTP(w, c.Request)

	assert.Equal(t, http.StatusRequestTimeout, w.Code)

	var response FetchMarketDataResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.False(t, response.Success)
	assert.Contains(t, response.Message, "Request timeout")
}

func TestConcurrentRequests(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test multiple concurrent requests
	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			
			reqBody := FetchMarketDataRequest{
				Symbols:  []string{fmt.Sprintf("TEST%d", id)},
				SourceID: "yahoo_finance",
			}

			reqBodyBytes, err := json.Marshal(reqBody)
			require.NoError(t, err)

			req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
			req.Header.Set("Content-Type", "application/json")

			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			assert.Equal(t, http.StatusOK, w.Code)

			var response FetchMarketDataResponse
			err = json.Unmarshal(w.Body.Bytes(), &response)
			require.NoError(t, err)
			assert.True(t, response.Success)
		}(i)
	}

	wg.Wait()
}

func TestLargePayload(t *testing.T) {
	router, mockClient := setupTestRouter()

	// Test with many symbols (100 symbols)
	symbols := make([]string, 100)
	for i := 0; i < 100; i++ {
		symbols[i] = fmt.Sprintf("SYMBOL%d", i)
	}

	reqBody := FetchMarketDataRequest{
		Symbols:  symbols,
		SourceID: "yahoo_finance",
	}

	reqBodyBytes, err := json.Marshal(reqBody)
	require.NoError(t, err)

	req, _ := http.NewRequest("POST", "/api/v1/market-data/fetch", bytes.NewReader(reqBodyBytes))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response FetchMarketDataResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.True(t, response.Success)
	assert.Equal(t, 100, len(response.MarketData))
}
