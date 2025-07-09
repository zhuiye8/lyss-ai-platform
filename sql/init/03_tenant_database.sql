-- Lyss AI Platform - 租户专用数据库表结构
-- 此脚本创建租户专用数据库的表结构，用于存储用户信息、对话、AI供应商配置等敏感数据

-- ===========================================
-- 1. 用户管理表
-- ===========================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL, -- 冗余字段，用于数据一致性检查
    
    -- 身份认证信息
    email CITEXT NOT NULL UNIQUE,
    username VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    
    -- 个人信息
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url VARCHAR(500),
    
    -- 状态和安全
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'inactive', 'suspended', 'deleted')),
    last_login_at TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    -- 邮箱验证
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    email_verification_expires TIMESTAMP WITH TIME ZONE,
    
    -- 密码重置
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP WITH TIME ZONE,
    
    -- 用户偏好设置
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 角色表
CREATE TABLE IF NOT EXISTS roles (
    role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(100) NOT NULL UNIQUE,
    role_description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb, -- 权限列表
    is_system_role BOOLEAN DEFAULT FALSE, -- 是否为系统预定义角色
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(user_id),
    expires_at TIMESTAMP WITH TIME ZONE NULL,
    PRIMARY KEY (user_id, role_id)
);

-- ===========================================
-- 2. AI供应商配置表
-- ===========================================

-- AI供应商凭证表（加密存储）
CREATE TABLE IF NOT EXISTS ai_credentials (
    credential_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    provider_name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(200), -- 用户友好的显示名称
    
    -- 加密存储的敏感信息
    encrypted_api_key TEXT, -- 加密后的API密钥
    encrypted_config TEXT, -- 加密后的其他配置信息
    
    -- 非敏感配置
    base_url VARCHAR(500),
    model_mappings JSONB, -- 模型映射配置
    rate_limits JSONB, -- 速率限制设置
    retry_config JSONB, -- 重试配置
    timeout_config JSONB, -- 超时配置
    
    -- 状态和元数据
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'inactive', 'testing', 'disabled')),
    last_tested_at TIMESTAMP WITH TIME ZONE,
    test_result JSONB, -- 最后测试结果
    usage_statistics JSONB, -- 使用统计
    
    -- 时间戳和审计
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),
    updated_by UUID REFERENCES users(user_id),
    
    UNIQUE(tenant_id, provider_name, display_name)
);

-- AI模型配置表
CREATE TABLE IF NOT EXISTS ai_models (
    model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    credential_id UUID NOT NULL REFERENCES ai_credentials(credential_id) ON DELETE CASCADE,
    model_name VARCHAR(200) NOT NULL, -- 供应商的模型名称
    model_alias VARCHAR(200), -- 内部别名
    model_type VARCHAR(50) NOT NULL, -- 'chat', 'completion', 'embedding', 'image'
    capabilities JSONB, -- 模型能力描述
    pricing JSONB, -- 定价信息
    context_window INTEGER,
    max_tokens INTEGER,
    supports_streaming BOOLEAN DEFAULT FALSE,
    supports_function_calling BOOLEAN DEFAULT FALSE,
    is_enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0, -- 优先级，用于模型选择
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- 3. 对话管理表
-- ===========================================

-- 对话表
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(500),
    summary TEXT,
    
    -- 对话配置
    model_config JSONB, -- 使用的模型配置
    system_prompt TEXT, -- 系统提示词
    
    -- 状态和统计
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'archived', 'deleted')),
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10, 6) DEFAULT 0.00,
    
    -- 元数据
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags JSONB, -- 标签
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    parent_message_id UUID REFERENCES messages(message_id), -- 支持消息树结构
    
    -- 消息内容
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- 'text', 'markdown', 'json'
    
    -- AI生成相关信息
    model_used VARCHAR(200), -- 使用的模型
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10, 6) DEFAULT 0.00,
    processing_time_ms INTEGER,
    
    -- 元数据和附件
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    attachments JSONB, -- 附件信息
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- ===========================================
-- 4. API密钥管理表
-- ===========================================

-- API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    api_key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_name VARCHAR(200) NOT NULL,
    encrypted_key_value TEXT NOT NULL, -- 加密后的API密钥值
    key_prefix VARCHAR(20) NOT NULL, -- 密钥前缀，用于显示
    
    -- 权限和限制
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    rate_limit_per_day INTEGER DEFAULT 10000,
    
    -- 状态和统计
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'inactive', 'revoked')),
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0,
    
    -- 过期和安全
    expires_at TIMESTAMP WITH TIME ZONE,
    allowed_ips INET[], -- 允许的IP地址
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, key_name)
);

-- ===========================================
-- 5. 索引创建
-- ===========================================

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- 角色表索引
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(role_name);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);

-- AI凭证表索引
CREATE INDEX IF NOT EXISTS idx_ai_credentials_tenant_id ON ai_credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_credentials_provider ON ai_credentials(provider_name);
CREATE INDEX IF NOT EXISTS idx_ai_credentials_status ON ai_credentials(status);
CREATE INDEX IF NOT EXISTS idx_ai_models_credential_id ON ai_models(credential_id);
CREATE INDEX IF NOT EXISTS idx_ai_models_type ON ai_models(model_type);

-- 对话表索引
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- 复合索引用于常见查询
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations(user_id, status);

-- API密钥表索引
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);

-- ===========================================
-- 6. 触发器函数
-- ===========================================

-- API密钥加密触发器函数
CREATE OR REPLACE FUNCTION encrypt_api_key()
RETURNS TRIGGER AS $$
BEGIN
    -- 加密API密钥
    IF NEW.encrypted_key_value IS NOT NULL AND 
       (OLD.encrypted_key_value IS NULL OR NEW.encrypted_key_value != OLD.encrypted_key_value) THEN
        NEW.encrypted_key_value = encrypt_data(NEW.encrypted_key_value, 'api_key');
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- AI凭证加密触发器函数
CREATE OR REPLACE FUNCTION encrypt_ai_credentials()
RETURNS TRIGGER AS $$
BEGIN
    -- 加密API密钥
    IF NEW.encrypted_api_key IS NOT NULL AND 
       (OLD.encrypted_api_key IS NULL OR NEW.encrypted_api_key != OLD.encrypted_api_key) THEN
        NEW.encrypted_api_key = encrypt_data(NEW.encrypted_api_key, 'ai_api_key');
    END IF;
    
    -- 加密配置信息
    IF NEW.encrypted_config IS NOT NULL AND 
       (OLD.encrypted_config IS NULL OR NEW.encrypted_config != OLD.encrypted_config) THEN
        NEW.encrypted_config = encrypt_data(NEW.encrypted_config, 'ai_config');
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 对话统计更新触发器函数
CREATE OR REPLACE FUNCTION update_conversation_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- 更新对话的消息数和最后消息时间
        UPDATE conversations 
        SET message_count = message_count + 1,
            last_message_at = NEW.created_at,
            total_tokens = total_tokens + NEW.total_tokens,
            estimated_cost = estimated_cost + NEW.estimated_cost,
            updated_at = CURRENT_TIMESTAMP
        WHERE conversation_id = NEW.conversation_id;
        
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- 更新对话的消息数
        UPDATE conversations 
        SET message_count = GREATEST(message_count - 1, 0),
            total_tokens = GREATEST(total_tokens - OLD.total_tokens, 0),
            estimated_cost = GREATEST(estimated_cost - OLD.estimated_cost, 0.00),
            updated_at = CURRENT_TIMESTAMP
        WHERE conversation_id = OLD.conversation_id;
        
        -- 更新最后消息时间
        UPDATE conversations 
        SET last_message_at = COALESCE(
            (SELECT MAX(created_at) FROM messages WHERE conversation_id = OLD.conversation_id),
            created_at
        )
        WHERE conversation_id = OLD.conversation_id;
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- 7. 创建触发器
-- ===========================================

-- updated_at触发器
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at 
    BEFORE UPDATE ON roles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_credentials_updated_at 
    BEFORE UPDATE ON ai_credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_models_updated_at 
    BEFORE UPDATE ON ai_models 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at 
    BEFORE UPDATE ON conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at 
    BEFORE UPDATE ON messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at 
    BEFORE UPDATE ON api_keys 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 加密触发器
CREATE TRIGGER encrypt_api_key_trigger
    BEFORE INSERT OR UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION encrypt_api_key();

CREATE TRIGGER encrypt_ai_credentials_trigger
    BEFORE INSERT OR UPDATE ON ai_credentials
    FOR EACH ROW EXECUTE FUNCTION encrypt_ai_credentials();

-- 对话统计触发器
CREATE TRIGGER update_conversation_stats_trigger
    AFTER INSERT OR DELETE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_conversation_stats();

-- ===========================================
-- 8. 行级安全策略
-- ===========================================

-- 启用行级安全
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- 创建租户隔离策略
CREATE POLICY tenant_isolation_users ON users
    FOR ALL TO PUBLIC
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_conversations ON conversations
    FOR ALL TO PUBLIC
    USING (user_id IN (SELECT user_id FROM users WHERE tenant_id = get_current_tenant_id()));

CREATE POLICY tenant_isolation_messages ON messages
    FOR ALL TO PUBLIC
    USING (user_id IN (SELECT user_id FROM users WHERE tenant_id = get_current_tenant_id()));

CREATE POLICY tenant_isolation_ai_credentials ON ai_credentials
    FOR ALL TO PUBLIC
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_api_keys ON api_keys
    FOR ALL TO PUBLIC
    USING (user_id IN (SELECT user_id FROM users WHERE tenant_id = get_current_tenant_id()));

-- 输出成功消息
DO $$
BEGIN
    RAISE NOTICE 'Lyss AI Platform - 租户专用数据库表结构创建成功';
END
$$;