package main

import (
	"context"
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
	"lyss-ai-platform/eino-service/internal/workflows"
	"lyss-ai-platform/eino-service/pkg/credential"
	"lyss-ai-platform/eino-service/pkg/health"
)

func main() {
	// 初始化日志
	logger := logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{})
	logger.SetLevel(logrus.InfoLevel)

	logger.Info("启动EINO服务...")

	// 加载配置
	cfg, err := config.LoadConfig("config.yaml")
	if err != nil {
		logger.WithError(err).Fatal("加载配置失败")
	}

	// 设置日志级别
	if level, err := logrus.ParseLevel(cfg.Logging.Level); err == nil {
		logger.SetLevel(level)
	}

	logger.WithFields(logrus.Fields{
		"port":           cfg.Server.Port,
		"database_host":  cfg.Database.Host,
		"database_port":  cfg.Database.Port,
		"redis_host":     cfg.Redis.Host,
		"redis_port":     cfg.Redis.Port,
		"tenant_service": cfg.Services.TenantService.BaseURL,
	}).Info("配置加载成功")

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
	credentialManager := credential.NewManager(
		tenantClient,
		redisClient,
		&cfg.Credential,
		logger,
	)

	// 启动凭证管理器
	if err := credentialManager.Start(); err != nil {
		logger.WithError(err).Fatal("凭证管理器启动失败")
	}
	logger.Info("凭证管理器启动成功")

	// 初始化健康检查器
	healthChecker := health.NewChecker(
		tenantClient,
		redisClient,
		credentialManager,
		logger,
	)

	// 初始化工作流管理器
	workflowManager := workflows.NewWorkflowManager(
		credentialManager,
		logger,
		cfg,
	)

	// 初始化工作流管理器
	if err := workflowManager.Initialize(); err != nil {
		logger.WithError(err).Fatal("工作流管理器初始化失败")
	}
	logger.Info("工作流管理器初始化成功")

	// 启动清理服务
	workflowManager.StartCleanupService()

	// 设置Gin模式
	if cfg.Logging.Level == "debug" {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}

	// 创建HTTP路由
	router := gin.New()

	// 添加基本中间件
	router.Use(gin.Recovery())
	router.Use(func(c *gin.Context) {
		c.Set("start_time", time.Now().UnixMilli())
		c.Next()
		c.Set("end_time", time.Now().UnixMilli())
	})

	// 初始化处理器
	healthHandler := handlers.NewHealthHandler(
		healthChecker,
		credentialManager,
		tenantClient,
		logger,
	)

	workflowHandler := handlers.NewWorkflowHandler(
		workflowManager,
		logger,
	)

	// 注册路由
	healthHandler.RegisterRoutes(router)
	workflowHandler.RegisterRoutes(router)

	// 创建HTTP服务器
	srv := &http.Server{
		Addr:           fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port),
		Handler:        router,
		ReadTimeout:    cfg.Server.ReadTimeout,
		WriteTimeout:   cfg.Server.WriteTimeout,
		IdleTimeout:    cfg.Server.IdleTimeout,
		MaxHeaderBytes: 1 << 20, // 1MB
	}

	// 启动服务器
	go func() {
		logger.WithFields(logrus.Fields{
			"address": srv.Addr,
			"version": "1.0.0",
		}).Info("HTTP服务器启动")

		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.WithError(err).Fatal("HTTP服务器启动失败")
		}
	}()

	// 等待中断信号
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("收到关闭信号，开始优雅关闭...")

	// 优雅关闭
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// 关闭HTTP服务器
	if err := srv.Shutdown(ctx); err != nil {
		logger.WithError(err).Error("HTTP服务器关闭失败")
	}

	// 关闭工作流管理器
	workflowManager.Shutdown()

	// 关闭凭证管理器
	credentialManager.Stop()

	// 关闭Redis连接
	if err := redisClient.Close(); err != nil {
		logger.WithError(err).Error("Redis连接关闭失败")
	}

	logger.Info("EINO服务已关闭")
}
