package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/lyss-ai/platform/eino-service/internal/config"
	"github.com/lyss-ai/platform/eino-service/internal/handlers"
	"github.com/lyss-ai/platform/eino-service/internal/middleware"
	"github.com/lyss-ai/platform/eino-service/internal/services"
	"github.com/lyss-ai/platform/eino-service/pkg/workflows"
)

func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Initialize services
	workflowService, err := services.NewWorkflowService(cfg)
	if err != nil {
		log.Fatalf("Failed to initialize workflow service: %v", err)
	}

	orchestratorService, err := services.NewOrchestratorService(cfg, workflowService)
	if err != nil {
		log.Fatalf("Failed to initialize orchestrator service: %v", err)
	}

	// Initialize workflow manager
	workflowManager, err := workflows.NewManager(cfg, workflowService)
	if err != nil {
		log.Fatalf("Failed to initialize workflow manager: %v", err)
	}

	// Register workflows
	if err := workflowManager.RegisterWorkflows(); err != nil {
		log.Fatalf("Failed to register workflows: %v", err)
	}

	// Setup Gin router
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	// Add middleware
	router.Use(gin.Recovery())
	router.Use(middleware.Logger())
	router.Use(middleware.CORS())
	router.Use(middleware.RequestID())
	router.Use(middleware.Metrics())

	// Health check endpoints
	router.GET("/health", handlers.HealthCheck)
	router.GET("/health/ready", handlers.ReadinessCheck)
	router.GET("/health/live", handlers.LivenessCheck)

	// Metrics endpoint
	router.GET("/metrics", handlers.MetricsHandler)

	// API routes
	v1 := router.Group("/api/v1")
	{
		// Workflow execution endpoints
		workflows := v1.Group("/workflows")
		{
			workflows.POST("/execute", handlers.ExecuteWorkflow(orchestratorService))
			workflows.GET("/status/:execution_id", handlers.GetWorkflowStatus(orchestratorService))
			workflows.POST("/cancel/:execution_id", handlers.CancelWorkflow(orchestratorService))
		}

		// Workflow management endpoints
		management := v1.Group("/management")
		{
			management.GET("/workflows", handlers.ListWorkflows(workflowManager))
			management.GET("/workflows/:workflow_id", handlers.GetWorkflowDetails(workflowManager))
			management.POST("/workflows/:workflow_id/validate", handlers.ValidateWorkflow(workflowManager))
		}
	}

	// WebSocket endpoint for real-time updates
	router.GET("/ws", handlers.WebSocketHandler(orchestratorService))

	// Create HTTP server
	server := &http.Server{
		Addr:    ":" + cfg.Server.Port,
		Handler: router,
	}

	// Start server in a goroutine
	go func() {
		log.Printf("Starting EINO service on port %s", cfg.Server.Port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	// Give outstanding requests 30 seconds to complete
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Printf("Server forced to shutdown: %v", err)
	}

	// Cleanup resources
	if err := workflowService.Close(); err != nil {
		log.Printf("Failed to close workflow service: %v", err)
	}

	if err := orchestratorService.Close(); err != nil {
		log.Printf("Failed to close orchestrator service: %v", err)
	}

	log.Println("Server exited")
}