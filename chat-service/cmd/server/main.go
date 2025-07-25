package main

import (
	"fmt"
	"log"

	"chat-service/configs"
	"chat-service/internal/handlers"
	"chat-service/internal/middleware"
	"chat-service/internal/models"
	"chat-service/internal/services"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func main() {
	// 加载配置
	config, err := configs.LoadConfig()
	if err != nil {
		log.Fatalf("配置加载失败: %v", err)
	}

	// 初始化数据库
	db, err := initDatabase(config)
	if err != nil {
		log.Fatalf("数据库初始化失败: %v", err)
	}

	// 自动迁移数据库表
	if err := migrateDatabase(db); err != nil {
		log.Fatalf("数据库迁移失败: %v", err)
	}

	// 初始化服务
	chatService := services.NewChatService(db, config)

	// 初始化处理器
	chatHandler := handlers.NewChatHandler(chatService)
	wsHandler := handlers.NewWebSocketHandler(chatService)

	// 初始化Gin路由
	if config.Server.Mode == "release" {
		gin.SetMode(gin.ReleaseMode)
	}
	router := gin.Default()

	// 注册中间件
	router.Use(middleware.CORSMiddleware())
	router.Use(middleware.RequestIDMiddleware())

	// 注册路由
	registerRoutes(router, chatHandler, wsHandler)

	// 启动服务器
	addr := fmt.Sprintf("%s:%d", config.Server.Host, config.Server.Port)
	log.Printf("Chat Service 启动成功，监听地址: %s", addr)
	
	if err := router.Run(addr); err != nil {
		log.Fatalf("服务器启动失败: %v", err)
	}
}

// initDatabase 初始化数据库连接
func initDatabase(config *configs.Config) (*gorm.DB, error) {
	dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
		config.Database.Host,
		config.Database.Port,
		config.Database.User,
		config.Database.Password,
		config.Database.Database,
		config.Database.SSLMode,
	)
	
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("数据库连接失败: %w", err)
	}
	
	// 测试连接
	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("获取数据库实例失败: %w", err)
	}
	
	if err := sqlDB.Ping(); err != nil {
		return nil, fmt.Errorf("数据库连接测试失败: %w", err)
	}
	
	log.Println("数据库连接成功")
	return db, nil
}

// migrateDatabase 执行数据库迁移
func migrateDatabase(db *gorm.DB) error {
	log.Println("开始数据库迁移...")
	
	// 自动迁移模型
	if err := db.AutoMigrate(
		&models.Conversation{},
		&models.Message{},
	); err != nil {
		return fmt.Errorf("数据库迁移失败: %w", err)
	}
	
	log.Println("数据库迁移完成")
	return nil
}

// registerRoutes 注册路由
func registerRoutes(router *gin.Engine, chatHandler *handlers.ChatHandler, wsHandler *handlers.WebSocketHandler) {
	// 健康检查（无需认证）
	router.GET("/health", chatHandler.GetHealth)
	router.GET("/metrics", chatHandler.GetMetrics)
	
	// API路由组（需要认证）
	api := router.Group("/api/v1")
	api.Use(middleware.AuthMiddleware())
	api.Use(middleware.TenantMiddleware())
	
	{
		// 对话管理
		conversations := api.Group("/conversations")
		{
			conversations.POST("", chatHandler.CreateConversation)
			conversations.GET("", chatHandler.ListConversations)
			conversations.GET("/:id", chatHandler.GetConversation)
			conversations.DELETE("/:id", chatHandler.DeleteConversation)
		}
		
		// 消息发送（同步）
		api.POST("/chat", chatHandler.SendMessage)
	}
	
	// WebSocket路由（需要认证）
	ws := router.Group("/ws")
	ws.Use(middleware.AuthMiddleware())
	ws.Use(middleware.TenantMiddleware())
	{
		ws.GET("/chat", wsHandler.HandleWebSocket)
	}
}