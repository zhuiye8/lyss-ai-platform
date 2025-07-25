package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// Metadata 自定义JSON字段类型
type Metadata map[string]interface{}

// Value 实现driver.Valuer接口
func (m Metadata) Value() (driver.Value, error) {
	if m == nil {
		return nil, nil
	}
	return json.Marshal(m)
}

// Scan 实现sql.Scanner接口
func (m *Metadata) Scan(value interface{}) error {
	if value == nil {
		*m = nil
		return nil
	}

	bytes, ok := value.([]byte)
	if !ok {
		return errors.New("无法扫描Metadata")
	}

	return json.Unmarshal(bytes, m)
}

// Conversation 对话记录模型
type Conversation struct {
	ID          string    `gorm:"primaryKey;type:varchar(36)" json:"id"`
	UserID      string    `gorm:"type:varchar(36);not null;index" json:"user_id"`
	TenantID    string    `gorm:"type:varchar(36);not null;index" json:"tenant_id"`
	Title       string    `gorm:"type:varchar(200);not null" json:"title"`
	Model       string    `gorm:"type:varchar(100);not null" json:"model"`
	Provider    string    `gorm:"type:varchar(50);not null" json:"provider"`
	Status      string    `gorm:"type:varchar(20);not null;default:'active'" json:"status"`
	MessageCount int      `gorm:"default:0" json:"message_count"`
	Metadata    Metadata  `gorm:"type:jsonb" json:"metadata"`
	CreatedAt   time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt   time.Time `gorm:"autoUpdateTime" json:"updated_at"`
	
	// 关联关系
	Messages []Message `gorm:"foreignKey:ConversationID" json:"messages,omitempty"`
}

// Message 消息记录模型
type Message struct {
	ID             string    `gorm:"primaryKey;type:varchar(36)" json:"id"`
	ConversationID string    `gorm:"type:varchar(36);not null;index" json:"conversation_id"`
	UserID         string    `gorm:"type:varchar(36);not null;index" json:"user_id"`
	TenantID       string    `gorm:"type:varchar(36);not null;index" json:"tenant_id"`
	Role           string    `gorm:"type:varchar(20);not null" json:"role"` // user, assistant, system
	Content        string    `gorm:"type:text;not null" json:"content"`
	Model          string    `gorm:"type:varchar(100)" json:"model"`
	Provider       string    `gorm:"type:varchar(50)" json:"provider"`
	TokensUsed     int       `gorm:"default:0" json:"tokens_used"`
	Cost           float64   `gorm:"type:decimal(10,6);default:0" json:"cost"`
	Status         string    `gorm:"type:varchar(20);not null;default:'completed'" json:"status"`
	Metadata       Metadata  `gorm:"type:jsonb" json:"metadata"`
	CreatedAt      time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt      time.Time `gorm:"autoUpdateTime" json:"updated_at"`
	
	// 关联关系
	Conversation Conversation `gorm:"foreignKey:ConversationID" json:"conversation,omitempty"`
}

// BeforeCreate GORM钩子 - 创建前设置ID
func (c *Conversation) BeforeCreate(tx *gorm.DB) error {
	if c.ID == "" {
		c.ID = uuid.New().String()
	}
	return nil
}

// BeforeCreate GORM钩子 - 创建前设置ID
func (m *Message) BeforeCreate(tx *gorm.DB) error {
	if m.ID == "" {
		m.ID = uuid.New().String()
	}
	return nil
}

// TableName 指定表名
func (Conversation) TableName() string {
	return "chat_conversations"
}

// TableName 指定表名
func (Message) TableName() string {
	return "chat_messages"
}

// ConversationStatus 对话状态枚举
const (
	ConversationStatusActive   = "active"
	ConversationStatusArchived = "archived"
	ConversationStatusDeleted  = "deleted"
)

// MessageRole 消息角色枚举
const (
	MessageRoleUser      = "user"
	MessageRoleAssistant = "assistant"
	MessageRoleSystem    = "system"
)

// MessageStatus 消息状态枚举
const (
	MessageStatusCompleted = "completed"
	MessageStatusPending   = "pending"
	MessageStatusFailed    = "failed"
	MessageStatusStreaming = "streaming"
)