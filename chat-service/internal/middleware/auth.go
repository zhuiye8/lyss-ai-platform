package middleware

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"chat-service/pkg/types"

	"github.com/gin-gonic/gin"
)

// AuthMiddleware JWT认证中间件
func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 获取Authorization头
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, types.ErrorResponse{
				Error:     "未提供认证令牌",
				Message:   "请在Authorization头中提供Bearer令牌",
				Code:      401,
				Timestamp: time.Now().Unix(),
			})
			c.Abort()
			return
		}
		
		// 检查Bearer前缀
		if !strings.HasPrefix(authHeader, "Bearer ") {
			c.JSON(http.StatusUnauthorized, types.ErrorResponse{
				Error:     "认证令牌格式错误",
				Message:   "Authorization头必须以'Bearer '开始",
				Code:      401,
				Timestamp: time.Now().Unix(),
			})
			c.Abort()
			return
		}
		
		// 提取token
		token := strings.TrimPrefix(authHeader, "Bearer ")
		if token == "" {
			c.JSON(http.StatusUnauthorized, types.ErrorResponse{
				Error:     "认证令牌为空",
				Message:   "Bearer令牌不能为空",
				Code:      401,
				Timestamp: time.Now().Unix(),
			})
			c.Abort()
			return
		}
		
		// TODO: 实际的JWT验证逻辑
		// 这里应该调用Auth Service验证JWT令牌
		// 现在使用简化的验证逻辑
		
		userInfo, err := validateJWTToken(token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, types.ErrorResponse{
				Error:     "认证令牌无效",
				Message:   err.Error(),
				Code:      401,
				Timestamp: time.Now().Unix(),
			})
			c.Abort()
			return
		}
		
		// 设置用户信息到上下文
		c.Set("user_id", userInfo.UserID)
		c.Set("tenant_id", userInfo.TenantID)
		c.Set("username", userInfo.Username)
		c.Set("roles", userInfo.Roles)
		
		c.Next()
	}
}

// UserInfo 用户信息结构
type UserInfo struct {
	UserID   string   `json:"user_id"`
	TenantID string   `json:"tenant_id"`
	Username string   `json:"username"`
	Roles    []string `json:"roles"`
}

// validateJWTToken 验证JWT令牌（简化实现）
func validateJWTToken(token string) (*UserInfo, error) {
	// TODO: 实现实际的JWT验证逻辑
	// 1. 解析JWT令牌
	// 2. 验证签名
	// 3. 检查过期时间
	// 4. 提取用户信息
	
	// 临时的模拟实现
	if token == "mock-jwt-token" {
		return &UserInfo{
			UserID:   "user-123",
			TenantID: "tenant-456", 
			Username: "testuser",
			Roles:    []string{"user"},
		}, nil
	}
	
	// 简单的token格式检查（生产环境应该删除）
	if len(token) < 20 {
		return nil, gin.Error{
			Err:  http.ErrMissingFile,
			Type: gin.ErrorTypePublic,
		}
	}
	
	// 返回模拟用户信息
	return &UserInfo{
		UserID:   "demo-user-id",
		TenantID: "demo-tenant-id",
		Username: "demouser",
		Roles:    []string{"user"},
	}, nil
}

// TenantMiddleware 租户验证中间件
func TenantMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		tenantID, exists := c.Get("tenant_id")
		if !exists || tenantID == "" {
			c.JSON(http.StatusBadRequest, types.ErrorResponse{
				Error:     "缺少租户信息",
				Message:   "请求中缺少有效的租户ID",
				Code:      400,
				Timestamp: time.Now().Unix(),
			})
			c.Abort()
			return
		}
		
		// TODO: 验证租户状态和权限
		// 这里可以检查租户是否有效、是否有权限访问聊天服务等
		
		c.Next()
	}
}

// CORSMiddleware CORS中间件
func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization")
		c.Header("Access-Control-Allow-Credentials", "true")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		
		c.Next()
	}
}

// RequestIDMiddleware 请求ID中间件
func RequestIDMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := c.GetHeader("X-Request-ID")
		if requestID == "" {
			requestID = generateRequestID()
		}
		
		c.Set("request_id", requestID)
		c.Header("X-Request-ID", requestID)
		
		c.Next()
	}
}

// generateRequestID 生成请求ID
func generateRequestID() string {
	// 简单的请求ID生成逻辑
	return fmt.Sprintf("req_%d", time.Now().UnixNano())
}