package pb

// Temporary placeholder types for compilation
// These will be replaced by actual protobuf-generated code

type MarketData struct {
	Symbol    string  `json:"symbol"`
	Price     float64 `json:"price"`
	Timestamp int64   `json:"timestamp"`
	Volume    int64   `json:"volume"`
}

type NewsData struct {
	ID          string  `json:"id"`
	Title       string  `json:"title"`
	Content     string  `json:"content"`
	Source      string  `json:"source"`
	Timestamp   int64   `json:"timestamp"`
}

type FetchMarketDataRequest struct {
	Symbols  []string `json:"symbols"`
	SourceID string   `json:"source_id"`
}

type FetchMarketDataResponse struct {
	Success    bool        `json:"success"`
	Message    string      `json:"message"`
	MarketData []MarketData `json:"market_data,omitempty"`
}

type FetchNewsDataRequest struct {
	SourceID string `json:"source_id"`
	Limit    int    `json:"limit"`
}

type FetchNewsDataResponse struct {
	Success  bool      `json:"success"`
	Message  string    `json:"message"`
	NewsData []NewsData `json:"news_data,omitempty"`
}

type HealthCheckRequest struct {
	ServiceName string            `json:"service_name"`
	Metadata    map[string]string `json:"metadata"`
}

type HealthCheckResponse struct {
	Healthy bool   `json:"healthy"`
	Status  string `json:"status"`
}

type EngineStatusResponse struct {
	Message string `json:"message"`
}

type Empty struct {
}

type ConnectDataSourceRequest struct {
	SourceID string `json:"source_id"`
	Config   map[string]interface{} `json:"config"`
}

type ConnectDataSourceResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

type GetMarketDataBufferRequest struct {
	SourceID string `json:"source_id"`
}

type GetMarketDataBufferResponse struct {
	Success    bool        `json:"success"`
	Message    string      `json:"message"`
	MarketData []MarketData `json:"market_data,omitempty"`
}

type GetNewsBufferRequest struct {
	SourceID string `json:"source_id"`
}

type GetNewsBufferResponse struct {
	Success  bool      `json:"success"`
	Message  string    `json:"message"`
	NewsData []NewsData `json:"news_data,omitempty"`
}

type GetIngestionStatsRequest struct {
	SourceID string `json:"source_id"`
}

type GetIngestionStatsResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Stats   map[string]interface{} `json:"stats"`
}
