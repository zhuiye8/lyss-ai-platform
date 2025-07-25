package handlers

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"time"

	"chat-service/internal/services"
	"chat-service/pkg/types"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

// WebSocketHandler WebSocket处理器
type WebSocketHandler struct {
	chatService *services.ChatService
	upgrader    websocket.Upgrader
}

// NewWebSocketHandler 创建WebSocket处理器
func NewWebSocketHandler(chatService *services.ChatService) *WebSocketHandler {
	return &WebSocketHandler{
		chatService: chatService,
		upgrader: websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize: 1024,
			CheckOrigin: func(r *http.Request) bool {
				// 生产环境中应该检查Origin
				return true
			},
		},
	}
}

// HandleWebSocket 处理WebSocket连接
func (h *WebSocketHandler) HandleWebSocket(c *gin.Context) {
	// 从请求中获取用户信息（应该通过JWT中间件注入）
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "未认证用户"})
		return
	}
	
	tenantID, exists := c.Get("tenant_id")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "缺少租户信息"})
		return
	}
	
	// 升级HTTP连接为WebSocket
	conn, err := h.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket升级失败: %v", err)
		return
	}
	defer conn.Close()
	
	log.Printf("用户 %s (租户: %s) 建立WebSocket连接", userID, tenantID)
	
	// 启动消息处理循环
	h.handleConnection(conn, userID.(string), tenantID.(string))
}

// handleConnection 处理WebSocket连接
func (h *WebSocketHandler) handleConnection(conn *websocket.Conn, userID, tenantID string) {
	// 设置连接超时和心跳
	conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	conn.SetPongHandler(func(string) error {
		conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})
	
	// 启动心跳goroutine
	go h.heartbeat(conn)
	
	// 消息处理循环
	for {
		var wsMsg types.WSMessage
		
		// 读取消息
		if err := conn.ReadJSON(&wsMsg); err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket读取错误: %v", err)
			}
			break
		}
		
		// 处理不同类型的消息
		switch wsMsg.Type {
		case types.WSMsgTypeChat:
			h.handleChatMessage(conn, userID, tenantID, wsMsg.Data)
		case types.WSMsgTypePing:
			h.sendMessage(conn, types.WSMessage{Type: types.WSMsgTypePong, Data: "pong"})
		case types.WSMsgTypeClose:
			log.Printf("客户端请求关闭连接")
			return
		default:
			log.Printf("未知消息类型: %s", wsMsg.Type)
		}
	}
}

// handleChatMessage 处理聊天消息
func (h *WebSocketHandler) handleChatMessage(conn *websocket.Conn, userID, tenantID string, data interface{}) {
	// 解析聊天请求
	dataBytes, err := json.Marshal(data)
	if err != nil {
		h.sendError(conn, "消息格式错误", err)
		return
	}
	
	var chatReq types.ChatRequest
	if err := json.Unmarshal(dataBytes, &chatReq); err != nil {
		h.sendError(conn, "聊天请求解析失败", err)
		return
	}
	
	// 验证请求
	if chatReq.Message == "" {
		h.sendError(conn, "消息内容不能为空", nil)
		return
	}
	
	ctx := context.Background()
	
	// 如果是流式请求，启动流式处理
	if chatReq.Stream {
		h.handleStreamChat(ctx, conn, userID, tenantID, &chatReq)
	} else {
		h.handleSyncChat(ctx, conn, userID, tenantID, &chatReq)
	}
}

// handleSyncChat 处理同步聊天
func (h *WebSocketHandler) handleSyncChat(ctx context.Context, conn *websocket.Conn, userID, tenantID string, req *types.ChatRequest) {
	// 调用聊天服务
	response, err := h.chatService.SendMessage(ctx, req.ConversationID, userID, tenantID, req)
	if err != nil {
		h.sendError(conn, "聊天处理失败", err)
		return
	}
	
	// 发送响应
	h.sendMessage(conn, types.WSMessage{
		Type: types.WSMsgTypeChat,
		Data: response,
	})
}

// handleStreamChat 处理流式聊天
func (h *WebSocketHandler) handleStreamChat(ctx context.Context, conn *websocket.Conn, userID, tenantID string, req *types.ChatRequest) {
	// TODO: 实现流式聊天
	// 这里需要与EINO的流式API集成
	
	log.Printf("开始处理流式聊天: user=%s, tenant=%s, message_length=%d", userID, tenantID, len(req.Message))
	
	// 使用ChatService的流式方法，真实集成EINO
	err := h.chatService.SendMessageStream(ctx, req.ConversationID, userID, tenantID, req, 
		func(chunk *types.ChatStreamChunk) error {
			// 将EINO流式响应转换为WebSocket消息格式并发送
			streamResp := types.StreamResponse{
				ConversationID: chunk.ConversationID,
				MessageID:      "", // 可以根据需要生成或获取实际的MessageID
				Delta:          chunk.Content,
				Done:           chunk.Done,
				Model:          req.Model,
				Provider:       req.Provider,
				Metadata:       chunk.Metadata,
			}
			
			wsMsg := types.WSMessage{
				Type: types.WSMsgTypeStream,
				Data: streamResp,
			}
			
			// 发送到WebSocket客户端
			h.sendMessage(conn, wsMsg)
			return nil
		})
	
	if err != nil {
		log.Printf("EINO流式聊天失败: %v", err)
		h.sendError(conn, "流式聊天处理失败", err)
		return
	}
	
	log.Printf("流式聊天处理完成: user=%s", userID)
}

// heartbeat 心跳机制
func (h *WebSocketHandler) heartbeat(conn *websocket.Conn) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			if err := conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				log.Printf("发送心跳失败: %v", err)
				return
			}
		}
	}
}

// sendMessage 发送WebSocket消息
func (h *WebSocketHandler) sendMessage(conn *websocket.Conn, msg types.WSMessage) {
	if err := conn.WriteJSON(msg); err != nil {
		log.Printf("发送WebSocket消息失败: %v", err)
	}
}

// sendError 发送错误消息
func (h *WebSocketHandler) sendError(conn *websocket.Conn, message string, err error) {
	errorMsg := types.WSMessage{
		Type: types.WSMsgTypeError,
		Data: types.ErrorResponse{
			Error:     "处理失败",
			Message:   message,
			Code:      500,
			Timestamp: time.Now().Unix(),
		},
	}
	
	if err != nil {
		log.Printf("WebSocket错误: %s - %v", message, err)
	}
	
	h.sendMessage(conn, errorMsg)
}

// generateTitle 生成对话标题
func (h *WebSocketHandler) generateTitle(message string) string {
	if len(message) > 30 {
		return message[:30] + "..."
	}
	return message
}