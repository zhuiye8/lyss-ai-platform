module github.com/zhuiye8/lyss-ai-platform/eino-service

go 1.18

require (
	github.com/cloudwego/eino v0.3.49
	github.com/gin-gonic/gin v1.10.0 // 修复CVE-2023-29401等安全漏洞
	github.com/golang-migrate/migrate/v4 v4.18.1 // 更新到最新稳定版本
	github.com/google/uuid v1.6.0 // 更新到最新版本，性能改进
	github.com/gorilla/websocket v1.5.3 // 修复DoS安全漏洞
	github.com/lib/pq v1.10.9 // 保持当前版本，考虑后续迁移到pgx
	github.com/prometheus/client_golang v1.20.5 // 修复多个CVE安全漏洞
	github.com/redis/go-redis/v9 v9.7.0 // 迁移到官方维护的新仓库，支持Redis 8
	github.com/sirupsen/logrus v1.9.3 // 保持当前版本，维护模式
	github.com/spf13/cobra v1.8.1 // 更新到最新版本
	github.com/spf13/viper v1.20.0 // 更新到最新版本
	github.com/stretchr/testify v1.10.0 // 更新测试框架到最新版本
	go.opentelemetry.io/otel v1.33.0 // 更新到最新版本
	go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp v1.33.0 // 替换弃用的jaeger导出器
	go.opentelemetry.io/otel/exporters/prometheus v0.55.0 // 更新prometheus导出器
	go.opentelemetry.io/otel/sdk v1.33.0 // 更新SDK到最新版本
	go.opentelemetry.io/otel/sdk/metric v1.33.0 // 更新metric SDK
	go.uber.org/zap v1.27.0 // 更新到最新版本，性能改进
	golang.org/x/time v0.8.0 // 更新到最新版本
	gorm.io/driver/postgres v1.5.10 // 更新到最新版本
	gorm.io/gorm v1.25.12 // 更新到最新版本
)
