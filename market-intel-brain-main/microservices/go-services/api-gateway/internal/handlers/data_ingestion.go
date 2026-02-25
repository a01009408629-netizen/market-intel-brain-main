package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/market-intel/api-gateway/internal/config"
	"github.com/market-intel/api-gateway/internal/services"
	"github.com/market-intel/api-gateway/pkg/logger"
)

// DataIngestionHandler handles data ingestion endpoints
type DataIngestionHandler struct {
	config           *config.Config
	coreEngineClient *services.CoreEngineClient
	upgrader         *websocket.Upgrader
}

// NewDataIngestionHandler creates a new data ingestion handler
func NewDataIngestionHandler(config *config.Config, coreEngineClient *services.CoreEngineClient) *DataIngestionHandler {
	return &DataIngestionHandler{
		config:           config,
		coreEngineClient: coreEngineClient,
		upgrader: &websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize: 1024,
		},
	}
}

// FetchMarketDataRequest represents the request for fetching market data
type FetchMarketDataRequest struct {
	Symbols  []string `json:"symbols" binding:"required"`
	SourceID string   `json:"source_id"`
}

// FetchMarketDataResponse represents the response for market data
type FetchMarketDataResponse struct {
	Success    bool                   `json:"success"`
	Message    string                 `json:"message"`
	MarketData []pb.MarketData        `json:"market_data,omitempty"`
	Metadata   map[string]interface{} `json:"metadata"`
	Timestamp  time.Time              `json:"timestamp"`
}

// FetchNewsDataRequest represents the request for fetching news data
type FetchNewsDataRequest struct {
	Keywords  []string `json:"keywords"`
	SourceID  string   `json:"source_id"`
	HoursBack int      `json:"hours_back"`
}

// FetchNewsDataResponse represents the response for news data
type FetchNewsDataResponse struct {
	Success    bool                 `json:"success"`
	Message    string               `json:"message"`
	NewsItems  []pb.NewsItem        `json:"news_items,omitempty"`
	Metadata   map[string]interface{} `json:"metadata"`
	Timestamp  time.Time             `json:"timestamp"`
}

// GetMarketDataBufferRequest represents the request for getting market data buffer
type GetMarketDataBufferRequest struct {
	Symbol string `json:"symbol"`
	Limit  int    `json:"limit"`
}

// GetMarketDataBufferResponse represents the response for market data buffer
type GetMarketDataBufferResponse struct {
	Success    bool                   `json:"success"`
	Message    string                 `json:"message"`
	MarketData []pb.MarketData        `json:"market_data,omitempty"`
	Metadata   map[string]interface{} `json:"metadata"`
	Timestamp  time.Time              `json:"timestamp"`
}

// GetNewsBufferRequest represents the request for getting news buffer
type GetNewsBufferRequest struct {
	Keywords []string `json:"keywords"`
	Limit    int      `json:"limit"`
}

// GetNewsBufferResponse represents the response for news buffer
type GetNewsBufferResponse struct {
	Success    bool                 `json:"success"`
	Message    string               `json:"message"`
	NewsItems  []pb.NewsItem        `json:"news_items,omitempty"`
	Metadata   map[string]interface{} `json:"metadata"`
	Timestamp  time.Time             `json:"timestamp"`
}

// ConnectDataSourceRequest represents the request for connecting to a data source
type ConnectDataSourceRequest struct {
	SourceID string `json:"source_id" binding:"required"`
	APIKey   string `json:"api_key"`
}

// ConnectDataSourceResponse represents the response for connecting to a data source
type ConnectDataSourceResponse struct {
	Success   bool                   `json:"success"`
	Message   string                 `json:"message"`
	Connected bool                   `json:"connected"`
	Metadata  map[string]interface{} `json:"metadata"`
	Timestamp time.Time              `json:"timestamp"`
}

// GetIngestionStatsResponse represents the response for ingestion statistics
type GetIngestionStatsResponse struct {
	Success   bool                   `json:"success"`
	Message   string                 `json:"message"`
	Stats     *pb.IngestionStats     `json:"stats,omitempty"`
	Metadata  map[string]interface{} `json:"metadata"`
	Timestamp time.Time              `json:"timestamp"`
}

// FetchMarketData handles the market data fetching endpoint
func (h *DataIngestionHandler) FetchMarketData(c *gin.Context) {
	startTime := time.Now()
	
	var req FetchMarketDataRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		logger.Errorf("Failed to bind request: %v", err)
		c.JSON(http.StatusBadRequest, FetchMarketDataResponse{
			Success:   false,
			Message:   "Invalid request format",
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Set default source if not provided
	if req.SourceID == "" {
		req.SourceID = "yahoo_finance"
	}

	// Validate request
	if len(req.Symbols) == 0 {
		c.JSON(http.StatusBadRequest, FetchMarketDataResponse{
			Success:   false,
			Message:   "At least one symbol is required",
			Metadata:  map[string]interface{}{"error": "empty_symbols"},
			Timestamp: startTime,
		})
		return
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()

	// Call Rust service
	response, err := h.coreEngineClient.FetchMarketData(ctx, &pb.FetchMarketDataRequest{
		Symbols:  req.Symbols,
		SourceId: req.SourceID,
	})

	if err != nil {
		logger.Errorf("Failed to fetch market data: %v", err)
		statusCode, message := h.mapGRPCToHTTPError(err)
		c.JSON(statusCode, FetchMarketDataResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Check response status
	if response.Status != pb.ResponseStatus_RESPONSE_STATUS_SUCCESS {
		statusCode, message := h.mapResponseStatus(response.Status)
		c.JSON(statusCode, FetchMarketDataResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"grpc_status": response.Status.String()},
			Timestamp: startTime,
		})
		return
	}

	// Prepare response metadata
	metadata := map[string]interface{}{
		"source_id":     req.SourceID,
		"symbols_count": len(req.Symbols),
		"response_time": time.Since(startTime).Seconds(),
		"grpc_status":   response.Status.String(),
	}

	logger.Infof("Successfully fetched market data for %d symbols from %s", len(req.Symbols), req.SourceID)

	c.JSON(http.StatusOK, FetchMarketDataResponse{
		Success:    true,
		Message:    response.Message,
		MarketData: response.MarketData,
		Metadata:   metadata,
		Timestamp:  startTime,
	})
}

// FetchNewsData handles the news data fetching endpoint
func (h *DataIngestionHandler) FetchNewsData(c *gin.Context) {
	startTime := time.Now()
	
	var req FetchNewsDataRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		logger.Errorf("Failed to bind request: %v", err)
		c.JSON(http.StatusBadRequest, FetchNewsDataResponse{
			Success:   false,
			Message:   "Invalid request format",
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Set defaults
	if req.SourceID == "" {
		req.SourceID = "news_api"
	}
	if req.HoursBack == 0 {
		req.HoursBack = 24
	}

	// Validate request
	if len(req.Keywords) == 0 {
		c.JSON(http.StatusBadRequest, FetchNewsDataResponse{
			Success:   false,
			Message:   "At least one keyword is required",
			Metadata:  map[string]interface{}{"error": "empty_keywords"},
			Timestamp: startTime,
		})
		return
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()

	// Call Rust service
	response, err := h.coreEngineClient.FetchNewsData(ctx, &pb.FetchNewsDataRequest{
		Keywords:  req.Keywords,
		SourceId:  req.SourceID,
		HoursBack: int32(req.HoursBack),
	})

	if err != nil {
		logger.Errorf("Failed to fetch news data: %v", err)
		statusCode, message := h.mapGRPCToHTTPError(err)
		c.JSON(statusCode, FetchNewsDataResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Check response status
	if response.Status != pb.ResponseStatus_RESPONSE_STATUS_SUCCESS {
		statusCode, message := h.mapResponseStatus(response.Status)
		c.JSON(statusCode, FetchNewsDataResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"grpc_status": response.Status.String()},
			Timestamp: startTime,
		})
		return
	}

	// Prepare response metadata
	metadata := map[string]interface{}{
		"source_id":     req.SourceID,
		"keywords_count": len(req.Keywords),
		"hours_back":    req.HoursBack,
		"response_time": time.Since(startTime).Seconds(),
		"grpc_status":   response.Status.String(),
	}

	logger.Infof("Successfully fetched %d news items for %d keywords from %s", 
		len(response.NewsItems), len(req.Keywords), req.SourceID)

	c.JSON(http.StatusOK, FetchNewsDataResponse{
		Success:   true,
		Message:   response.Message,
		NewsItems: response.NewsItems,
		Metadata:  metadata,
		Timestamp: startTime,
	})
}

// GetMarketDataBuffer handles getting market data from buffer
func (h *DataIngestionHandler) GetMarketDataBuffer(c *gin.Context) {
	startTime := time.Now()
	
	symbol := c.Query("symbol")
	limitStr := c.DefaultQuery("limit", "100")
	
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 100
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	// Call Rust service
	response, err := h.coreEngineClient.GetMarketDataBuffer(ctx, &pb.GetMarketDataBufferRequest{
		Symbol: symbol,
		Limit:  int32(limit),
	})

	if err != nil {
		logger.Errorf("Failed to get market data buffer: %v", err)
		statusCode, message := h.mapGRPCToHTTPError(err)
		c.JSON(statusCode, GetMarketDataBufferResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Check response status
	if response.Status != pb.ResponseStatus_RESPONSE_STATUS_SUCCESS {
		statusCode, message := h.mapResponseStatus(response.Status)
		c.JSON(statusCode, GetMarketDataBufferResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"grpc_status": response.Status.String()},
			Timestamp: startTime,
		})
		return
	}

	// Prepare response metadata
	metadata := map[string]interface{}{
		"symbol":        symbol,
		"limit":         limit,
		"items_count":   len(response.MarketData),
		"response_time": time.Since(startTime).Seconds(),
		"grpc_status":   response.Status.String(),
	}

	logger.Infof("Retrieved %d market data items from buffer", len(response.MarketData))

	c.JSON(http.StatusOK, GetMarketDataBufferResponse{
		Success:    true,
		Message:    response.Message,
		MarketData: response.MarketData,
		Metadata:   metadata,
		Timestamp:  startTime,
	})
}

// GetNewsBuffer handles getting news from buffer
func (h *DataIngestionHandler) GetNewsBuffer(c *gin.Context) {
	startTime := time.Now()
	
	keywords := c.QueryArray("keywords")
	limitStr := c.DefaultQuery("limit", "100")
	
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 100
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	// Call Rust service
	response, err := h.coreEngineClient.GetNewsBuffer(ctx, &pb.GetNewsBufferRequest{
		Keywords: keywords,
		Limit:    int32(limit),
	})

	if err != nil {
		logger.Errorf("Failed to get news buffer: %v", err)
		statusCode, message := h.mapGRPCToHTTPError(err)
		c.JSON(statusCode, GetNewsBufferResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Check response status
	if response.Status != pb.ResponseStatus_RESPONSE_STATUS_SUCCESS {
		statusCode, message := h.mapResponseStatus(response.Status)
		c.JSON(statusCode, GetNewsBufferResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"grpc_status": response.Status.String()},
			Timestamp: startTime,
		})
		return
	}

	// Prepare response metadata
	metadata := map[string]interface{}{
		"keywords":      keywords,
		"limit":         limit,
		"items_count":   len(response.NewsItems),
		"response_time": time.Since(startTime).Seconds(),
		"grpc_status":   response.Status.String(),
	}

	logger.Infof("Retrieved %d news items from buffer", len(response.NewsItems))

	c.JSON(http.StatusOK, GetNewsBufferResponse{
		Success:   true,
		Message:   response.Message,
		NewsItems: response.NewsItems,
		Metadata:  metadata,
		Timestamp: startTime,
	})
}

// GetIngestionStats handles getting ingestion statistics
func (h *DataIngestionHandler) GetIngestionStats(c *gin.Context) {
	startTime := time.Now()

	// Create context with timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	// Call Rust service
	response, err := h.coreEngineClient.GetIngestionStats(ctx, &pb.Empty{})

	if err != nil {
		logger.Errorf("Failed to get ingestion stats: %v", err)
		statusCode, message := h.mapGRPCToHTTPError(err)
		c.JSON(statusCode, GetIngestionStatsResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Check response status
	if response.Status != pb.ResponseStatus_RESPONSE_STATUS_SUCCESS {
		statusCode, message := h.mapResponseStatus(response.Status)
		c.JSON(statusCode, GetIngestionStatsResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"grpc_status": response.Status.String()},
			Timestamp: startTime,
		})
		return
	}

	// Prepare response metadata
	metadata := map[string]interface{}{
		"response_time": time.Since(startTime).Seconds(),
		"grpc_status":   response.Status.String(),
	}

	logger.Info("Retrieved ingestion statistics")

	c.JSON(http.StatusOK, GetIngestionStatsResponse{
		Success:   true,
		Message:   response.Message,
		Stats:     response.Stats,
		Metadata:  metadata,
		Timestamp: startTime,
	})
}

// ConnectDataSource handles connecting to a data source
func (h *DataIngestionHandler) ConnectDataSource(c *gin.Context) {
	startTime := time.Now()
	
	var req ConnectDataSourceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		logger.Errorf("Failed to bind request: %v", err)
		c.JSON(http.StatusBadRequest, ConnectDataSourceResponse{
			Success:   false,
			Message:   "Invalid request format",
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Validate request
	if req.SourceID == "" {
		c.JSON(http.StatusBadRequest, ConnectDataSourceResponse{
			Success:   false,
			Message:   "Source ID is required",
			Metadata:  map[string]interface{}{"error": "empty_source_id"},
			Timestamp: startTime,
		})
		return
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()

	// Call Rust service
	response, err := h.coreEngineClient.ConnectDataSource(ctx, &pb.ConnectDataSourceRequest{
		SourceId: req.SourceID,
		ApiKey:   req.APIKey,
	})

	if err != nil {
		logger.Errorf("Failed to connect to data source: %v", err)
		statusCode, message := h.mapGRPCToHTTPError(err)
		c.JSON(statusCode, ConnectDataSourceResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"error": err.Error()},
			Timestamp: startTime,
		})
		return
	}

	// Check response status
	if response.Status != pb.ResponseStatus_RESPONSE_STATUS_SUCCESS {
		statusCode, message := h.mapResponseStatus(response.Status)
		c.JSON(statusCode, ConnectDataSourceResponse{
			Success:   false,
			Message:   message,
			Metadata:  map[string]interface{}{"grpc_status": response.Status.String()},
			Timestamp: startTime,
		})
		return
	}

	// Prepare response metadata
	metadata := map[string]interface{}{
		"source_id":     req.SourceID,
		"has_api_key":   req.APIKey != "",
		"response_time": time.Since(startTime).Seconds(),
		"grpc_status":   response.Status.String(),
	}

	logger.Infof("Successfully connected to data source: %s", req.SourceID)

	c.JSON(http.StatusOK, ConnectDataSourceResponse{
		Success:   true,
		Message:   response.Message,
		Connected: response.Connected,
		Metadata:  metadata,
		Timestamp: startTime,
	})
}

// WebSocketMarketData handles WebSocket connections for real-time market data
func (h *DataIngestionHandler) WebSocketMarketData(c *gin.Context) {
	// Upgrade HTTP connection to WebSocket
	conn, err := h.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		logger.Errorf("Failed to upgrade to WebSocket: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to upgrade to WebSocket"})
		return
	}
	defer conn.Close()

	logger.Info("WebSocket market data connection established")

	// Handle WebSocket messages in a goroutine
	go h.handleWebSocketMarketData(conn)
}

// handleWebSocketMarketData handles WebSocket messages for market data
func (h *DataIngestionHandler) handleWebSocketMarketData(conn *websocket.Conn) {
	for {
		// Read message from client
		messageType, message, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				logger.Infof("WebSocket connection closed: %v", err)
			} else {
				logger.Errorf("WebSocket read error: %v", err)
			}
			break
		}

		// Handle different message types
		switch messageType {
		case websocket.TextMessage:
			// Parse JSON message
			var req FetchMarketDataRequest
			if err := json.Unmarshal(message, &req); err != nil {
				logger.Errorf("Failed to unmarshal WebSocket message: %v", err)
				h.sendWebSocketError(conn, "Invalid message format")
				continue
			}

			// Process market data request
			go h.processWebSocketMarketDataRequest(conn, req)

		case websocket.BinaryMessage:
			logger.Warn("Binary message not supported")
			h.sendWebSocketError(conn, "Binary messages not supported")

		case websocket.CloseMessage:
			logger.Info("WebSocket close message received")
			return

		case websocket.PingMessage:
			// Respond with pong
			conn.WriteMessage(websocket.PongMessage, message)
		}
	}
}

// processWebSocketMarketDataRequest processes market data requests from WebSocket
func (h *DataIngestionHandler) processWebSocketMarketDataRequest(conn *websocket.Conn, req FetchMarketDataRequest) {
	startTime := time.Now()

	// Set default source if not provided
	if req.SourceID == "" {
		req.SourceID = "yahoo_finance"
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Call Rust service
	response, err := h.coreEngineClient.FetchMarketData(ctx, &pb.FetchMarketDataRequest{
		Symbols:  req.Symbols,
		SourceId: req.SourceID,
	})

	// Prepare response
	responseData := map[string]interface{}{
		"timestamp": startTime,
		"success":   err == nil && response.Status == pb.ResponseStatus_RESPONSE_STATUS_SUCCESS,
	}

	if err != nil {
		responseData["error"] = err.Error()
		responseData["grpc_error"] = true
	} else {
		responseData["message"] = response.Message
		responseData["market_data"] = response.MarketData
		responseData["grpc_status"] = response.Status.String()
	}

	// Convert to JSON and send
	jsonResponse, err := json.Marshal(responseData)
	if err != nil {
		logger.Errorf("Failed to marshal WebSocket response: %v", err)
		return
	}

	if err := conn.WriteMessage(websocket.TextMessage, jsonResponse); err != nil {
		logger.Errorf("Failed to send WebSocket response: %v", err)
	}
}

// sendWebSocketError sends an error message over WebSocket
func (h *DataIngestionHandler) sendWebSocketError(conn *websocket.Conn, message string) {
	errorResponse := map[string]interface{}{
		"timestamp": time.Now(),
		"success":   false,
		"error":     message,
	}

	jsonResponse, err := json.Marshal(errorResponse)
	if err != nil {
		logger.Errorf("Failed to marshal WebSocket error response: %v", err)
		return
	}

	if err := conn.WriteMessage(websocket.TextMessage, jsonResponse); err != nil {
		logger.Errorf("Failed to send WebSocket error: %v", err)
	}
}

// mapGRPCToHTTPError maps gRPC errors to HTTP status codes
func (h *DataIngestionHandler) mapGRPCToHTTPError(err error) (int, string) {
	if grpcErr, ok := status.FromError(err); ok {
		return mapGRPCToHTTPStatus(grpcErr.Code())
	}
	
	// Non-gRPC errors
	return http.StatusInternalServerError, err.Error()
}

// mapGRPCToHTTPStatus maps gRPC status codes to HTTP status codes
func mapGRPCToHTTPStatus(grpcStatus codes.Code) (int, string) {
	switch grpcStatus {
	case codes.OK:
		return http.StatusOK, "Success"
	case codes.Canceled:
		return http.StatusRequestTimeout, "Request canceled"
	case codes.Unknown:
		return http.StatusInternalServerError, "Unknown error"
	case codes.InvalidArgument:
		return http.StatusBadRequest, "Invalid argument"
	case codes.DeadlineExceeded:
		return http.StatusRequestTimeout, "Deadline exceeded"
	case codes.NotFound:
		return http.StatusNotFound, "Not found"
	case codes.AlreadyExists:
		return http.StatusConflict, "Already exists"
	case codes.PermissionDenied:
		return http.StatusForbidden, "Permission denied"
	case codes.Unauthenticated:
		return http.StatusUnauthorized, "Unauthorized"
	case codes.ResourceExhausted:
		return http.StatusTooManyRequests, "Resource exhausted"
	case codes.FailedPrecondition:
		return http.StatusPreconditionFailed, "Failed precondition"
	case codes.Aborted:
		return http.StatusConflict, "Aborted"
	case codes.OutOfRange:
		return http.StatusBadRequest, "Out of range"
	case codes.Unimplemented:
		return http.StatusNotImplemented, "Unimplemented"
	case codes.Internal:
		return http.StatusInternalServerError, "Internal error"
	case codes.Unavailable:
		return http.StatusServiceUnavailable, "Service unavailable"
	case codes.DataLoss:
		return http.StatusInternalServerError, "Data loss"
	default:
		return http.StatusInternalServerError, "Unknown error"
	}
}
