package services

import (
	"context"
	"fmt"
	"log"
	"time"

	"chat-service/configs"
	"chat-service/internal/models"
	"chat-service/pkg/types"
	"chat-service/pkg/utils"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// ChatService 聊天服务
type ChatService struct {
	db             *gorm.DB
	config         *configs.Config
	providerClient *utils.ProviderClient // Provider Service客户端
}

// NewChatService 创建聊天服务实例
func NewChatService(db *gorm.DB, config *configs.Config) *ChatService {
	service := &ChatService{
		db:             db,
		config:         config,
		providerClient: utils.NewProviderClient(config),
	}
	
	log.Println("ChatService初始化完成，已集成Provider Service客户端")
	
	return service
}

// CreateConversation 创建新对话
func (s *ChatService) CreateConversation(ctx context.Context, userID, tenantID, title, model, provider string) (*models.Conversation, error) {
	conversation := &models.Conversation{
		ID:       uuid.New().String(),
		UserID:   userID,
		TenantID: tenantID,
		Title:    title,
		Model:    model,
		Provider: provider,
		Status:   models.ConversationStatusActive,
		Metadata: make(models.Metadata),
	}
	
	if err := s.db.WithContext(ctx).Create(conversation).Error; err != nil {
		return nil, fmt.Errorf("创建对话失败: %w", err)
	}
	
	return conversation, nil
}

// GetConversation 获取对话详情
func (s *ChatService) GetConversation(ctx context.Context, conversationID, userID, tenantID string) (*models.Conversation, error) {
	var conversation models.Conversation
	
	err := s.db.WithContext(ctx).
		Where("id = ? AND user_id = ? AND tenant_id = ?", conversationID, userID, tenantID).
		Preload("Messages", func(db *gorm.DB) *gorm.DB {
			return db.Order("created_at ASC")
		}).
		First(&conversation).Error
	
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, fmt.Errorf("对话不存在")
		}
		return nil, fmt.Errorf("获取对话失败: %w", err)
	}
	
	return &conversation, nil
}

// ListConversations 获取用户对话列表
func (s *ChatService) ListConversations(ctx context.Context, userID, tenantID string, req *types.ConversationListRequest) (*types.ConversationListResponse, error) {
	var conversations []models.Conversation
	var total int64
	
	query := s.db.WithContext(ctx).
		Where("user_id = ? AND tenant_id = ?", userID, tenantID)
	
	// 添加状态过滤
	if req.Status != "" {
		query = query.Where("status = ?", req.Status)
	}
	
	// 添加模型过滤
	if req.Model != "" {
		query = query.Where("model = ?", req.Model)
	}
	
	// 计算总数
	if err := query.Model(&models.Conversation{}).Count(&total).Error; err != nil {
		return nil, fmt.Errorf("统计对话数量失败: %w", err)
	}
	
	// 分页查询
	offset := (req.Page - 1) * req.PageSize
	if err := query.Order("updated_at DESC").
		Offset(offset).
		Limit(req.PageSize).
		Find(&conversations).Error; err != nil {
		return nil, fmt.Errorf("查询对话列表失败: %w", err)
	}
	
	// 转换为响应格式
	summaries := make([]types.ConversationSummary, len(conversations))
	for i, conv := range conversations {
		summaries[i] = types.ConversationSummary{
			ID:           conv.ID,
			Title:        conv.Title,
			Model:        conv.Model,
			Provider:     conv.Provider,
			MessageCount: conv.MessageCount,
			UpdatedAt:    conv.UpdatedAt,
			Metadata:     map[string]interface{}(conv.Metadata),
		}
		
		// 获取最后一条消息
		var lastMessage models.Message
		if err := s.db.WithContext(ctx).
			Where("conversation_id = ?", conv.ID).
			Order("created_at DESC").
			First(&lastMessage).Error; err == nil {
			// 截取前50个字符作为摘要
			content := lastMessage.Content
			if len(content) > 50 {
				content = content[:50] + "..."
			}
			summaries[i].LastMessage = content
		}
	}
	
	return &types.ConversationListResponse{
		Conversations: summaries,
		Total:         total,
		Page:          req.Page,
		PageSize:      req.PageSize,
		HasMore:       int64(offset+req.PageSize) < total,
	}, nil
}

// SendMessage 发送消息（同步模式）
func (s *ChatService) SendMessage(ctx context.Context, conversationID, userID, tenantID string, req *types.ChatRequest) (*types.ChatResponse, error) {
	// 获取或创建对话
	conversation, err := s.getOrCreateConversation(ctx, conversationID, userID, tenantID, req)
	if err != nil {
		return nil, fmt.Errorf("获取对话失败: %w", err)
	}
	
	// 创建用户消息记录
	userMessage := &models.Message{
		ConversationID: conversation.ID,
		UserID:         userID,
		TenantID:       tenantID,
		Role:           models.MessageRoleUser,
		Content:        req.Message,
		Status:         models.MessageStatusCompleted,
		Metadata:       make(models.Metadata),
	}
	
	if err := s.db.WithContext(ctx).Create(userMessage).Error; err != nil {
		return nil, fmt.Errorf("保存用户消息失败: %w", err)
	}
	
	// 调用AI模型生成回复
	response, err := s.callAIModel(ctx, conversation, req)
	if err != nil {
		return nil, fmt.Errorf("AI模型调用失败: %w", err)
	}
	
	// 创建AI回复消息记录
	aiMessage := &models.Message{
		ConversationID: conversation.ID,
		UserID:         userID,
		TenantID:       tenantID,
		Role:           models.MessageRoleAssistant,
		Content:        response.Content,
		Model:          response.Model,
		Provider:       response.Provider,
		TokensUsed:     response.TokensUsed,
		Cost:           response.Cost,
		Status:         models.MessageStatusCompleted,
		Metadata:       models.Metadata(response.Metadata),
	}
	
	if err := s.db.WithContext(ctx).Create(aiMessage).Error; err != nil {
		return nil, fmt.Errorf("保存AI回复失败: %w", err)
	}
	
	// 更新对话的消息计数
	if err := s.db.WithContext(ctx).Model(conversation).
		UpdateColumn("message_count", gorm.Expr("message_count + ?", 2)).Error; err != nil {
		log.Printf("更新对话消息计数失败: %v", err)
	}
	
	return &types.ChatResponse{
		ConversationID: conversation.ID,
		MessageID:      aiMessage.ID,
		Content:        response.Content,
		Model:          response.Model,
		Provider:       response.Provider,
		TokensUsed:     response.TokensUsed,
		Cost:           response.Cost,
		Metadata:       response.Metadata,
		CreatedAt:      aiMessage.CreatedAt,
	}, nil
}

// getOrCreateConversation 获取或创建对话
func (s *ChatService) getOrCreateConversation(ctx context.Context, conversationID, userID, tenantID string, req *types.ChatRequest) (*models.Conversation, error) {
	if conversationID != "" {
		// 尝试获取现有对话
		conversation, err := s.GetConversation(ctx, conversationID, userID, tenantID)
		if err == nil {
			return conversation, nil
		}
	}
	
	// 创建新对话
	model := req.Model
	if model == "" {
		model = s.config.EINO.DefaultProvider
	}
	
	provider := req.Provider
	if provider == "" {
		provider = s.config.EINO.DefaultProvider
	}
	
	title := s.generateConversationTitle(req.Message)
	
	return s.CreateConversation(ctx, userID, tenantID, title, model, provider)
}

// callAIModel 调用AI模型（通过Provider Service）
func (s *ChatService) callAIModel(ctx context.Context, conversation *models.Conversation, req *types.ChatRequest) (*types.ChatResponse, error) {
	// 验证模型是否支持
	if !s.providerClient.ValidateModel(conversation.Model) {
		return nil, fmt.Errorf("不支持的AI模型: %s", conversation.Model)
	}
	
	// 构建消息历史
	messageHistory := s.buildMessageHistoryForProvider(ctx, conversation.ID)
	
	// 添加当前用户消息
	messageHistory = append(messageHistory, utils.Message{
		Role:    "user",
		Content: req.Message,
	})
	
	log.Printf("调用Provider Service: model=%s, history_length=%d", 
		conversation.Model, len(messageHistory))
	
	// 通过Provider Service调用AI模型
	providerResponse, err := s.providerClient.CallModel(
		ctx, 
		conversation.Model, 
		messageHistory,
		conversation.UserID,
	)
	if err != nil {
		return nil, fmt.Errorf("Provider Service调用失败: %w", err)
	}
	
	// 转换为ChatService响应格式
	response := &types.ChatResponse{
		Content:    providerResponse.Content,
		Model:      providerResponse.Model,
		Provider:   providerResponse.Provider,
		TokensUsed: providerResponse.TokensUsed,
		Cost:       providerResponse.Cost,
		Metadata:   providerResponse.Metadata,
	}
	
	log.Printf("Provider Service调用成功: tokens=%d, cost=%.6f", providerResponse.TokensUsed, providerResponse.Cost)
	
	return response, nil
}

// generateConversationTitle 生成对话标题
func (s *ChatService) generateConversationTitle(message string) string {
	if len(message) > 30 {
		return message[:30] + "..."
	}
	return message
}

// buildMessageHistoryForProvider 构建消息历史（用于Provider Service）
func (s *ChatService) buildMessageHistoryForProvider(ctx context.Context, conversationID string) []utils.Message {
	var messages []models.Message
	
	// 获取最近的消息历史（限制数量以控制上下文长度）
	if err := s.db.WithContext(ctx).
		Where("conversation_id = ?", conversationID).
		Order("created_at ASC").
		Limit(20). // 限制最近20条消息
		Find(&messages).Error; err != nil {
		log.Printf("获取消息历史失败: %v", err)
		return nil
	}
	
	// 转换为ProviderClient兼容格式
	historyMessages := make([]utils.Message, len(messages))
	for i, msg := range messages {
		historyMessages[i] = utils.Message{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}
	
	log.Printf("构建消息历史: conversation_id=%s, message_count=%d", conversationID, len(historyMessages))
	
	return historyMessages
}

// SendMessageStream 发送消息（流式模式）
func (s *ChatService) SendMessageStream(ctx context.Context, conversationID, userID, tenantID string, req *types.ChatRequest, callback func(chunk *types.ChatStreamChunk) error) error {
	// 获取或创建对话
	conversation, err := s.getOrCreateConversation(ctx, conversationID, userID, tenantID, req)
	if err != nil {
		return fmt.Errorf("获取对话失败: %w", err)
	}
	
	// 创建用户消息记录
	userMessage := &models.Message{
		ConversationID: conversation.ID,
		UserID:         userID,
		TenantID:       tenantID,
		Role:           models.MessageRoleUser,
		Content:        req.Message,
		Status:         models.MessageStatusCompleted,
		Metadata:       make(models.Metadata),
	}
	
	if err := s.db.WithContext(ctx).Create(userMessage).Error; err != nil {
		return fmt.Errorf("保存用户消息失败: %w", err)
	}
	
	// 验证模型支持
	if !s.providerClient.ValidateModel(conversation.Model) {
		return fmt.Errorf("不支持的AI模型: %s", conversation.Model)
	}
	
	// 构建消息历史
	messageHistory := s.buildMessageHistoryForProvider(ctx, conversation.ID)
	messageHistory = append(messageHistory, utils.Message{
		Role:    "user",
		Content: req.Message,
	})
	
	log.Printf("开始流式调用Provider Service: model=%s", conversation.Model)
	
	// 用于收集完整响应的变量
	var fullContent string
	var totalTokens int
	var totalCost float64
	
	// 调用Provider Service流式生成
	err = s.providerClient.CallModelStream(ctx, conversation.Model, messageHistory, conversation.UserID,
		func(chunk utils.StreamChunk) error {
			// 累积内容
			fullContent += chunk.Content
			
			// 发送流式响应给客户端
			streamChunk := &types.ChatStreamChunk{
				ConversationID: conversation.ID,
				Content:        chunk.Content,
				Done:           chunk.Done,
				Metadata:       chunk.Metadata,
			}
			
			return callback(streamChunk)
		})
	
	if err != nil {
		return fmt.Errorf("Provider Service流式调用失败: %w", err)
	}
	
	// 流式调用完成后，保存AI回复消息
	aiMessage := &models.Message{
		ConversationID: conversation.ID,
		UserID:         userID,
		TenantID:       tenantID,
		Role:           models.MessageRoleAssistant,
		Content:        fullContent,
		Model:          conversation.Model,
		Provider:       conversation.Provider,
		TokensUsed:     totalTokens,
		Cost:           totalCost,
		Status:         models.MessageStatusCompleted,
		Metadata: models.Metadata{
			"provider_service": true,
			"stream_mode":      true,
			"timestamp":        time.Now().Unix(),
		},
	}
	
	if err := s.db.WithContext(ctx).Create(aiMessage).Error; err != nil {
		log.Printf("保存AI流式回复失败: %v", err)
	}
	
	// 更新对话消息计数
	if err := s.db.WithContext(ctx).Model(conversation).
		UpdateColumn("message_count", gorm.Expr("message_count + ?", 2)).Error; err != nil {
		log.Printf("更新对话消息计数失败: %v", err)
	}
	
	log.Printf("Provider Service流式调用完成: content_length=%d", len(fullContent))
	
	return nil
}

// DeleteConversation 删除对话
func (s *ChatService) DeleteConversation(ctx context.Context, conversationID, userID, tenantID string) error {
	// 软删除对话
	result := s.db.WithContext(ctx).
		Model(&models.Conversation{}).
		Where("id = ? AND user_id = ? AND tenant_id = ?", conversationID, userID, tenantID).
		Update("status", models.ConversationStatusDeleted)
	
	if result.Error != nil {
		return fmt.Errorf("删除对话失败: %w", result.Error)
	}
	
	if result.RowsAffected == 0 {
		return fmt.Errorf("对话不存在或无权限删除")
	}
	
	return nil
}