package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/services"
	"github.com/market-intel/api-gateway/pkg/logger"
	pb "github.com/market-intel/api-gateway/pb"
)

// DataIngestionHandler handles data ingestion endpoints
type DataIngestionHandler struct {
	config           *config.Config
	coreEngineClient services.CoreEngineInterface
	upgrader         *websocket.Upgrader
}

// NewDataIngestionHandler creates a new data ingestion handler
func NewDataIngestionHandler(config *config.Config, coreEngineClient services.CoreEngineInterface) *DataIngestionHandler {
	return &DataIngestionHandler{
		config:           config,
		coreEngineClient: coreEngineClient,
		upgrader: &websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize:  1024,
		},
	}
}

// FetchMarketDataRequest represents a request for fetching market data
type FetchMarketDataRequest struct {
	Symbols  []string `json:"symbols" binding:"required"`
	SourceID string   `json:"source_id"`
}

// FetchMarketDataResponse represents a response for market data
type FetchMarketDataResponse struct {
	Success    bool                   `json:"success"`
	Message    string                 `json:"message"`
	MarketData []pb.MarketData        `json:"market_data,omitempty"`
}

// FetchNewsDataRequest represents a request for fetching news data
type FetchNewsDataRequest struct {
	SourceID string `json:"source_id"`
	Limit    int    `json:"limit"`
}

// FetchNewsDataResponse represents a response for news data
type FetchNewsDataResponse struct {
	Success  bool           `json:"success"`
	Message  string         `json:"message"`
	NewsData []pb.NewsData   `json:"news_data,omitempty"`
}

// HealthCheckResponse represents a response for health check
type HealthCheckResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// ConnectDataSourceRequest represents a request for connecting data source
type ConnectDataSourceRequest struct {
	SourceID string                 `json:"source_id"`
	Config   map[string]interface{}   `json:"config"`
}

// ConnectDataSourceResponse represents a response for connecting data source
type ConnectDataSourceResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// GetMarketDataBufferRequest represents a request for getting market data buffer
type GetMarketDataBufferRequest struct {
	SourceID string `json:"source_id"`
}

// GetMarketDataBufferResponse represents a response for market data buffer
type GetMarketDataBufferResponse struct {
	Success    bool                   `json:"success"`
	Message    string                 `json:"message"`
	MarketData []pb.MarketData        `json:"market_data,omitempty"`
}

// GetNewsBufferRequest represents a request for getting news buffer
type GetNewsBufferRequest struct {
	SourceID string `json:"source_id"`
}

// GetNewsBufferResponse represents a response for news buffer
type GetNewsBufferResponse struct {
	Success  bool           `json:"success"`
	Message  string         `json:"message"`
	NewsData []pb.NewsData   `json:"news_data,omitempty"`
}

// GetIngestionStatsRequest represents a request for getting ingestion stats
type GetIngestionStatsRequest struct {
	SourceID string `json:"source_id"`
}

// GetIngestionStatsResponse represents a response for ingestion stats
type GetIngestionStatsResponse struct {
	Success bool                   `json:"success"`
	Message string                 `json:"message"`
	Stats   map[string]interface{} `json:"stats,omitempty"`
}

// FetchMarketData handles HTTP POST request to fetch market data
func (h *DataIngestionHandler) FetchMarketData(c *gin.Context) {
	var req FetchMarketDataRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		logger.Errorf("Invalid request format: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "Invalid request format",
		})
		return
	}

	logger.Infof("Fetching market data for symbols: %v from source: %s", req.Symbols, req.SourceID)

	// Create protobuf request
	pbReq := &pb.FetchMarketDataRequest{
		Symbols:  req.Symbols,
		SourceID: req.SourceID,
	}

	// Call core engine with circuit breaker
	err := h.coreEngineClient.ExecuteWithCircuitBreaker(c.Request.Context(), func() error {
		var err error
		_, err = h.coreEngineClient.FetchMarketData(c.Request.Context(), pbReq)
		return err
	})

	if err != nil {
		logger.Errorf("Failed to fetch market data: %v", err)
		c.JSON(h.mapResponseStatus(err), FetchMarketDataResponse{
			Success: false,
			Message: "Failed to fetch market data",
		})
		return
	}

	// Return success response
	c.JSON(http.StatusOK, FetchMarketDataResponse{
		Success: true,
		Message: "Market data fetched successfully",
	})
}

// FetchNewsData handles HTTP POST request to fetch news data
func (h *DataIngestionHandler) FetchNewsData(c *gin.Context) {
	var req FetchNewsDataRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		logger.Errorf("Invalid request format: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "Invalid request format",
		})
		return
	}

	logger.Infof("Fetching news data from source: %s with limit: %d", req.SourceID, req.Limit)

	// Create protobuf request
	pbReq := &pb.FetchNewsDataRequest{
		SourceID: req.SourceID,
		Limit:    req.Limit,
	}

	// Call core engine with circuit breaker
	err := h.coreEngineClient.ExecuteWithCircuitBreaker(c.Request.Context(), func() error {
		var err error
		_, err = h.coreEngineClient.FetchNewsData(c.Request.Context(), pbReq)
		return err
	})

	if err != nil {
		logger.Errorf("Failed to fetch news data: %v", err)
		c.JSON(h.mapResponseStatus(err), FetchNewsDataResponse{
			Success: false,
			Message: "Failed to fetch news data",
		})
		return
	}

	// Return success response
	c.JSON(http.StatusOK, FetchNewsDataResponse{
		Success: true,
		Message: "News data fetched successfully",
	})
}

// ConnectDataSource handles HTTP POST request to connect a data source
func (h *DataIngestionHandler) ConnectDataSource(c *gin.Context) {
	var req ConnectDataSourceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		logger.Errorf("Invalid request format: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "Invalid request format",
		})
		return
	}

	logger.Infof("Connecting data source: %s", req.SourceID)

	// Create protobuf request
	pbReq := &pb.ConnectDataSourceRequest{
		SourceID: req.SourceID,
		Config:   req.Config,
	}

	// Call core engine with circuit breaker
	err := h.coreEngineClient.ExecuteWithCircuitBreaker(c.Request.Context(), func() error {
		var err error
		_, err = h.coreEngineClient.ConnectDataSource(c.Request.Context(), pbReq)
		return err
	})

	if err != nil {
		logger.Errorf("Failed to connect data source: %v", err)
		c.JSON(h.mapResponseStatus(err), ConnectDataSourceResponse{
			Success: false,
			Message: "Failed to connect data source",
		})
		return
	}

	// Return success response
	c.JSON(http.StatusOK, ConnectDataSourceResponse{
		Success: true,
		Message: "Data source connected successfully",
	})
}

// HealthCheck handles HTTP GET request for health check
func (h *DataIngestionHandler) HealthCheck(c *gin.Context) {
	serviceName := c.Query("service")
	if serviceName == "" {
		serviceName = "api-gateway"
	}

	logger.Infof("Health check for service: %s", serviceName)

	// Call core engine health check
	err := h.coreEngineClient.HealthCheck(c.Request.Context(), serviceName)
	if err != nil {
		logger.Errorf("Health check failed: %v", err)
		c.JSON(h.mapResponseStatus(err), HealthCheckResponse{
			Success: false,
			Message: "Health check failed",
		})
		return
	}

	// Return success response
	c.JSON(http.StatusOK, HealthCheckResponse{
		Success: true,
		Message: "Service is healthy",
	})
}

// GetMarketDataBuffer handles HTTP GET request for market data buffer
func (h *DataIngestionHandler) GetMarketDataBuffer(c *gin.Context) {
	sourceID := c.Query("source_id")
	if sourceID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "source_id query parameter is required",
		})
		return
	}

	logger.Infof("Getting market data buffer for source: %s", sourceID)

	// Create protobuf request
	pbReq := &pb.GetMarketDataBufferRequest{
		SourceID: sourceID,
	}

	// Call core engine with circuit breaker
	err := h.coreEngineClient.ExecuteWithCircuitBreaker(c.Request.Context(), func() error {
		var err error
		_, err = h.coreEngineClient.GetMarketDataBuffer(c.Request.Context(), pbReq)
		return err
	})

	if err != nil {
		logger.Errorf("Failed to get market data buffer: %v", err)
		c.JSON(h.mapResponseStatus(err), GetMarketDataBufferResponse{
			Success: false,
			Message: "Failed to get market data buffer",
		})
		return
	}

	// Return success response
	c.JSON(http.StatusOK, GetMarketDataBufferResponse{
		Success: true,
		Message: "Market data buffer retrieved successfully",
	})
}

// GetNewsBuffer handles HTTP GET request for news buffer
func (h *DataIngestionHandler) GetNewsBuffer(c *gin.Context) {
	sourceID := c.Query("source_id")
	if sourceID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "source_id query parameter is required",
		})
		return
	}

	logger.Infof("Getting news buffer for source: %s", sourceID)

	// Create protobuf request
	pbReq := &pb.GetNewsBufferRequest{
		SourceID: sourceID,
	}

	// Call core engine with circuit breaker
	err := h.coreEngineClient.ExecuteWithCircuitBreaker(c.Request.Context(), func() error {
		var err error
		_, err = h.coreEngineClient.GetNewsBuffer(c.Request.Context(), pbReq)
		return err
	})

	if err != nil {
		logger.Errorf("Failed to get news buffer: %v", err)
		c.JSON(h.mapResponseStatus(err), GetNewsBufferResponse{
			Success: false,
			Message: "Failed to get news buffer",
		})
		return
	}

	// Return success response
	c.JSON(http.StatusOK, GetNewsBufferResponse{
		Success: true,
		Message: "News buffer retrieved successfully",
	})
}

// GetIngestionStats handles HTTP GET request for ingestion stats
func (h *DataIngestionHandler) GetIngestionStats(c *gin.Context) {
	sourceID := c.Query("source_id")
	if sourceID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"success": false,
			"message": "source_id query parameter is required",
		})
		return
	}

	logger.Infof("Getting ingestion stats for source: %s", sourceID)

	// Create protobuf request
	pbReq := &pb.GetIngestionStatsRequest{
		SourceID: sourceID,
	}

	// Call core engine with circuit breaker
	err := h.coreEngineClient.ExecuteWithCircuitBreaker(c.Request.Context(), func() error {
		var err error
		_, err = h.coreEngineClient.GetIngestionStats(c.Request.Context(), pbReq)
		return err
	})

	if err != nil {
		logger.Errorf("Failed to get ingestion stats: %v", err)
		c.JSON(h.mapResponseStatus(err), GetIngestionStatsResponse{
			Success: false,
			Message: "Failed to get ingestion stats",
		})
		return
	}

	// Return success response
	c.JSON(http.StatusOK, GetIngestionStatsResponse{
		Success: true,
		Message: "Ingestion stats retrieved successfully",
	})
}

// HandleWebSocket handles WebSocket connections for real-time data
func (h *DataIngestionHandler) HandleWebSocket(c *gin.Context) {
	conn, err := h.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		logger.Errorf("Failed to upgrade to WebSocket: %v", err)
		return
	}
	defer conn.Close()

	logger.Infof("WebSocket connection established")

	for {
		messageType, p, err := conn.ReadMessage()
		if err != nil {
			logger.Errorf("Failed to read WebSocket message: %v", err)
			break
		}

		if messageType == websocket.TextMessage {
			logger.Infof("Received WebSocket message: %s", string(p))
			
			// Echo back the message for now
			if err := conn.WriteMessage(messageType, p); err != nil {
				logger.Errorf("Failed to write WebSocket message: %v", err)
				break
			}
		}
	}
}

// WebSocketMarketData handles WebSocket connections for market data streaming
func (h *DataIngestionHandler) WebSocketMarketData(c *gin.Context) {
	conn, err := h.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		logger.Errorf("Failed to upgrade to WebSocket: %v", err)
		return
	}
	defer conn.Close()

	logger.Infof("Market data WebSocket connection established")

	for {
		messageType, p, err := conn.ReadMessage()
		if err != nil {
			logger.Errorf("Failed to read WebSocket message: %v", err)
			break
		}

		if messageType == websocket.TextMessage {
			logger.Infof("Received market data WebSocket message: %s", string(p))
			
			// Echo back the message for now
			if err := conn.WriteMessage(messageType, p); err != nil {
				logger.Errorf("Failed to write WebSocket message: %v", err)
				break
			}
		}
	}
}

// mapResponseStatus maps gRPC status to HTTP status code
func (h *DataIngestionHandler) mapResponseStatus(grpcErr error) int {
	if grpcErr == nil {
		return http.StatusOK
	}

	st, ok := status.FromError(grpcErr)
	if !ok {
		return http.StatusInternalServerError
	}

	switch st.Code() {
	case codes.InvalidArgument:
		return http.StatusBadRequest
	case codes.NotFound:
		return http.StatusNotFound
	case codes.PermissionDenied:
		return http.StatusForbidden
	case codes.Unauthenticated:
		return http.StatusUnauthorized
	case codes.DeadlineExceeded:
		return http.StatusRequestTimeout
	case codes.ResourceExhausted:
		return http.StatusTooManyRequests
	case codes.Unavailable:
		return http.StatusServiceUnavailable
	default:
		return http.StatusInternalServerError
	}
}
