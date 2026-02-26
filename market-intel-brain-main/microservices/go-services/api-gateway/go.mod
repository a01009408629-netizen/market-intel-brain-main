module github.com/market-intel/api-gateway

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/golang/protobuf v1.5.3
	github.com/sirupsen/logrus v1.9.3
	google.golang.org/grpc v1.58.0
	google.golang.org/protobuf v1.31.0
	github.com/gorilla/websocket v1.5.0
	github.com/joho/godotenv v1.4.0
	golang.org/x/time v0.3.0
	github.com/prometheus/client_golang v1.18.0
	go.opentelemetry.io/otel v1.24.0
	go.opentelemetry.io/otel/sdk v1.24.0
	go.opentelemetry.io/otel/trace v1.24.0
	go.opentelemetry.io/otel/exporters/jaeger v1.17.0
	go.opentelemetry.io/otel/exporters/prometheus v0.46.0
	go.opentelemetry.io/otel/sdk/metric v1.24.0
	go.opentelemetry.io/otel/sdk/resource v1.24.0
	go.opentelemetry.io/semconv/v1.21.0/semconv v1.21.0
)
