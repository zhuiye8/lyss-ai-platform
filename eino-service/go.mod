module github.com/lyss-ai/platform/eino-service

go 1.21

require (
	github.com/cloudwego/eino v0.2.0
	github.com/cloudwego/eino-ext v0.1.0
	github.com/gin-gonic/gin v1.9.1
	github.com/go-redis/redis/v8 v8.11.5
	github.com/golang-migrate/migrate/v4 v4.16.2
	github.com/google/uuid v1.4.0
	github.com/gorilla/websocket v1.5.1
	github.com/lib/pq v1.10.9
	github.com/prometheus/client_golang v1.17.0
	github.com/sirupsen/logrus v1.9.3
	github.com/spf13/cobra v1.8.0
	github.com/spf13/viper v1.17.0
	github.com/stretchr/testify v1.8.4
	go.opentelemetry.io/otel v1.21.0
	go.opentelemetry.io/otel/exporters/jaeger v1.17.0
	go.opentelemetry.io/otel/exporters/prometheus v0.44.0
	go.opentelemetry.io/otel/sdk v1.21.0
	go.opentelemetry.io/otel/sdk/metric v1.21.0
	go.uber.org/zap v1.26.0
	golang.org/x/time v0.5.0
	gorm.io/driver/postgres v1.5.4
	gorm.io/gorm v1.25.5
)