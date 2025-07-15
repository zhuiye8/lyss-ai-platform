package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/client"
	"lyss-ai-platform/eino-service/internal/config"
	"lyss-ai-platform/eino-service/internal/handlers"
	"lyss-ai-platform/eino-service/pkg/credential"
	"lyss-ai-platform/eino-service/pkg/health"
)

var (
	configFile = flag.String("config", "config.yaml", "配置文件路径")
	version    = "1.0.0"
)

func main() {
	flag.Parse()
	
	// 初始化日志
	logger := logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{})
	logger.SetLevel(logrus.InfoLevel)
	
	logger.WithField("version", version).Info("EINO Service 启动中...")
	
	// 加载配置
	cfg, err := config.LoadConfig(*configFile)
	if err != nil {
		logger.WithError(err).Fatal("加载配置文件失败")
	}
	
	// 设置日志级别
	if level, err := logrus.ParseLevel(cfg.Logging.Level); err == nil {
		logger.SetLevel(level)
	}
	
	// 初始化Redis客户端
	redisClient := redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%d", cfg.Redis.Host, cfg.Redis.Port),
		Password: cfg.Redis.Password,
		DB:       cfg.Redis.DB,
	})
	
	// 测试Redis连接
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	if err := redisClient.Ping(ctx).Err(); err != nil {
		logger.WithError(err).Fatal("Redis连接失败")
	}
	logger.Info("Redis连接成功")
	
	// 初始化租户服务客户端
	tenantClient := client.NewTenantClient(&cfg.Services.TenantService, logger)
	
	// 测试租户服务连接
	if err := tenantClient.HealthCheck(ctx); err != nil {
		logger.WithError(err).Fatal("租户服务连接失败")
	}
	logger.Info("租户服务连接成功")
	
	// 初始化凭证管理器
	credentialManager := credential.NewManager(tenantClient, redisClient, &cfg.Credential, logger)
	
	// 启动凭证管理器
	if err := credentialManager.Start(); err != nil {
		logger.WithError(err).Fatal("启动凭证管理器失败")
	}
	
	// 初始化健康检查器
	healthChecker := health.NewChecker(tenantClient, redisClient, credentialManager, logger)
	
	// 初始化HTTP处理器
	chatHandler := handlers.NewChatHandler(credentialManager, logger)
	healthHandler := handlers.NewHealthHandler(healthChecker, logger)
	
	// 设置Gin模式
	if cfg.Logging.Level == "debug" {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}
	
	// 创建路由
	router := setupRoutes(chatHandler, healthHandler)
	
	// 创建HTTP服务器
	server := &http.Server{
		Addr:         fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port),
		Handler:      router,
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
		IdleTimeout:  cfg.Server.IdleTimeout,
	}
	
	// 启动服务器
	go func() {
		logger.WithField("address", server.Addr).Info("EINO Service 启动成功")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.WithError(err).Fatal("HTTP服务器启动失败")
		}
	}()
	
	// 等待中断信号
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	
	logger.Info("开始优雅关闭...")
	
	// 关闭HTTP服务器
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	
	if err := server.Shutdown(ctx); err != nil {
		logger.WithError(err).Error("HTTP服务器关闭失败")
	}
	
	// 停止凭证管理器
	credentialManager.Stop()
	
	// 关闭Redis连接
	if err := redisClient.Close(); err != nil {
		logger.WithError(err).Error("Redis连接关闭失败")
	}
	
	logger.Info("EINO Service 已关闭")
}

// setupRoutes 设置路由
func setupRoutes(chatHandler *handlers.ChatHandler, healthHandler *handlers.HealthHandler) *gin.Engine {
	router := gin.New()
	
	// 中间件
	router.Use(gin.Logger())
	router.Use(gin.Recovery())
	
	// 添加CORS中间件
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Request-ID, X-User-ID, X-Tenant-ID")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		
		c.Next()
	})
	
	// 添加请求ID中间件
	router.Use(func(c *gin.Context) {
		requestID := c.GetHeader("X-Request-ID")
		if requestID == "" {
			requestID = fmt.Sprintf("req-%d", time.Now().UnixNano())
		}
		c.Set("request_id", requestID)
		c.Header("X-Request-ID", requestID)
		c.Next()
	})
	
	// 健康检查
	router.GET("/health", healthHandler.HealthCheck)
	
	// API路由
	v1 := router.Group("/api/v1")
	{
		// 聊天接口
		chat := v1.Group("/chat")
		{
			chat.POST("/simple", chatHandler.SimpleChat)
			chat.POST("/stream", chatHandler.StreamChat)
			chat.POST("/rag", chatHandler.RAGChat)
		}
		
		// 工作流执行状态查询
		v1.GET("/executions/:execution_id", chatHandler.GetExecution)
	}
	
	// 根路径
	router.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "Lyss EINO Service",
			"version": version,
			"status":  "running",
			"docs":    "/docs",
		})
	})
	
	return router
}