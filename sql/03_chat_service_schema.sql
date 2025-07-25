-- Chat Service 数据库表结构
-- 创建时间: 2025-01-24
-- 描述: Chat Service的对话和消息管理表

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建对话表
CREATE TABLE IF NOT EXISTS chat_conversations (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    title VARCHAR(200) NOT NULL,
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    conversation_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    model VARCHAR(100),
    provider VARCHAR(50),
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(10,6) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
-- 对话表索引
CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_tenant ON chat_conversations(user_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_tenant ON chat_conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_status ON chat_conversations(status);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_model ON chat_conversations(model);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated_at ON chat_conversations(updated_at DESC);

-- 消息表索引
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_tenant ON chat_messages(user_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_tenant ON chat_messages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_model ON chat_messages(model);

-- 添加外键约束
ALTER TABLE chat_messages 
ADD CONSTRAINT fk_chat_messages_conversation 
FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE;

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为对话表创建更新时间触发器
DROP TRIGGER IF EXISTS update_chat_conversations_updated_at ON chat_conversations;
CREATE TRIGGER update_chat_conversations_updated_at
    BEFORE UPDATE ON chat_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为消息表创建更新时间触发器
DROP TRIGGER IF EXISTS update_chat_messages_updated_at ON chat_messages;
CREATE TRIGGER update_chat_messages_updated_at
    BEFORE UPDATE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 创建消息计数更新触发器函数
CREATE OR REPLACE FUNCTION update_conversation_message_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE chat_conversations 
        SET message_count = message_count + 1 
        WHERE id = NEW.conversation_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE chat_conversations 
        SET message_count = message_count - 1 
        WHERE id = OLD.conversation_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

-- 创建消息计数触发器
DROP TRIGGER IF EXISTS trigger_update_message_count ON chat_messages;
CREATE TRIGGER trigger_update_message_count
    AFTER INSERT OR DELETE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_message_count();

-- 插入初始测试数据（开发环境）
DO $$
BEGIN
    -- 检查是否为开发环境（基于数据库名称）
    IF current_database() = 'lyss_db' THEN
        -- 插入测试对话
        INSERT INTO chat_conversations (id, user_id, tenant_id, title, model, provider, status)
        VALUES 
            ('demo-conversation-1', 'demo-user-id', 'demo-tenant-id', '测试对话1', 'gpt-3.5-turbo', 'openai', 'active'),
            ('demo-conversation-2', 'demo-user-id', 'demo-tenant-id', '测试对话2', 'claude-3', 'anthropic', 'active')
        ON CONFLICT (id) DO NOTHING;
        
        -- 插入测试消息
        INSERT INTO chat_messages (id, conversation_id, user_id, tenant_id, role, content, model, provider, status)
        VALUES 
            ('demo-message-1', 'demo-conversation-1', 'demo-user-id', 'demo-tenant-id', 'user', '你好，请介绍一下自己', 'gpt-3.5-turbo', 'openai', 'completed'),
            ('demo-message-2', 'demo-conversation-1', 'demo-user-id', 'demo-tenant-id', 'assistant', '你好！我是一个AI助手，很高兴为你服务。', 'gpt-3.5-turbo', 'openai', 'completed'),
            ('demo-message-3', 'demo-conversation-2', 'demo-user-id', 'demo-tenant-id', 'user', '今天天气怎么样？', 'claude-3', 'anthropic', 'completed'),
            ('demo-message-4', 'demo-conversation-2', 'demo-user-id', 'demo-tenant-id', 'assistant', '很抱歉，我无法获取实时天气信息。建议您查看天气应用或网站。', 'claude-3', 'anthropic', 'completed')
        ON CONFLICT (id) DO NOTHING;
        
        RAISE NOTICE '已插入Chat Service测试数据';
    END IF;
END $$;

-- 创建视图：对话摘要视图
CREATE OR REPLACE VIEW chat_conversation_summary AS
SELECT 
    c.id,
    c.user_id,
    c.tenant_id,
    c.title,
    c.model,
    c.provider,
    c.status,
    c.message_count,
    c.created_at,
    c.updated_at,
    COALESCE(last_msg.content, '') as last_message,
    COALESCE(last_msg.created_at, c.created_at) as last_message_at
FROM chat_conversations c
LEFT JOIN LATERAL (
    SELECT content, created_at
    FROM chat_messages m
    WHERE m.conversation_id = c.id
    ORDER BY m.created_at DESC
    LIMIT 1
) last_msg ON true;

-- 创建统计函数：获取用户对话统计
CREATE OR REPLACE FUNCTION get_user_chat_stats(p_user_id VARCHAR(36), p_tenant_id VARCHAR(36))
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_conversations', COUNT(DISTINCT c.id),
        'total_messages', COALESCE(SUM(c.message_count), 0),
        'active_conversations', COUNT(DISTINCT CASE WHEN c.status = 'active' THEN c.id END),
        'models_used', json_agg(DISTINCT c.model),
        'providers_used', json_agg(DISTINCT c.provider),
        'first_conversation_at', MIN(c.created_at),
        'last_conversation_at', MAX(c.updated_at)
    ) INTO result
    FROM chat_conversations c
    WHERE c.user_id = p_user_id AND c.tenant_id = p_tenant_id;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- 添加注释
COMMENT ON TABLE chat_conversations IS 'Chat Service对话表 - 存储用户对话会话信息';
COMMENT ON TABLE chat_messages IS 'Chat Service消息表 - 存储对话中的消息记录';
COMMENT ON VIEW chat_conversation_summary IS 'Chat Service对话摘要视图 - 包含最后一条消息的对话列表';
COMMENT ON FUNCTION get_user_chat_stats IS 'Chat Service用户统计函数 - 获取用户的对话统计信息';

-- 权限设置（如果需要）
-- GRANT SELECT, INSERT, UPDATE, DELETE ON chat_conversations TO lyss_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON chat_messages TO lyss_user;
-- GRANT SELECT ON chat_conversation_summary TO lyss_user;

COMMIT;