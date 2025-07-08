# 数据库设计文档

## 1. 数据库架构概述

### 1.1 多租户数据库策略
- **混合多租户模型**：核心敏感数据采用"每个租户一个数据库"模式，大容量非关键数据使用共享数据库
- **主数据库**：存储租户基础信息和路由配置
- **租户专用数据库**：存储用户信息、角色权限、供应商凭证等敏感数据
- **共享数据库**：存储审计日志、使用统计等大容量数据

### 1.2 数据库技术选型
- **主数据库**：PostgreSQL 15+
- **扩展插件**：pgcrypto（列级加密）、pg_stat_statements（性能监控）
- **连接池**：PgBouncer
- **备份策略**：WAL-E + AWS S3（或兼容存储）

## 2. 数据库Schema设计

### 2.1 主数据库 (master_db)

#### 2.1.1 租户管理表
```sql
-- 租户主表
CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name VARCHAR(255) NOT NULL UNIQUE,
    tenant_slug VARCHAR(100) NOT NULL UNIQUE, -- URL友好的租户标识
    db_connection_string TEXT NOT NULL, -- 租户专用数据库连接字符串
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    subscription_plan VARCHAR(50) DEFAULT 'basic',
    max_users INTEGER DEFAULT 10,
    max_api_calls_per_month INTEGER DEFAULT 10000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 租户配置表
CREATE TABLE tenant_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, config_key)
);

-- 索引
CREATE INDEX idx_tenants_slug ON tenants(tenant_slug);
CREATE INDEX idx_tenants_status ON tenants(status);
CREATE INDEX idx_tenant_configs_tenant_id ON tenant_configs(tenant_id);
```

#### 2.1.2 系统配置表
```sql
-- 系统全局配置
CREATE TABLE system_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI供应商模板配置
CREATE TABLE ai_provider_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(100) NOT NULL UNIQUE,
    provider_type VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'google', 'custom'
    base_url VARCHAR(500),
    auth_method VARCHAR(50) NOT NULL, -- 'api_key', 'oauth', 'basic_auth'
    required_fields JSONB NOT NULL, -- 必需的配置字段
    optional_fields JSONB, -- 可选配置字段
    rate_limits JSONB, -- 默认速率限制
    pricing_info JSONB, -- 定价信息
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 租户专用数据库 (tenant_{tenant_id})

#### 2.2.1 用户管理表
```sql
-- 用户表
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL, -- 冗余字段，便于数据一致性检查
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    last_login_at TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 角色表
CREATE TABLE roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(100) NOT NULL UNIQUE,
    role_description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]', -- 权限列表
    is_system_role BOOLEAN DEFAULT FALSE, -- 是否为系统预定义角色
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 用户角色关联表
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(user_id),
    PRIMARY KEY (user_id, role_id)
);

-- 索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
```

#### 2.2.2 AI供应商配置表
```sql
-- 供应商凭证表（加密存储）
CREATE TABLE ai_provider_credentials (
    credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider_name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(200), -- 用户友好的显示名称
    -- 加密字段
    encrypted_api_key BYTEA, -- 使用 pgcrypto 加密
    encrypted_config BYTEA, -- 其他加密配置信息
    -- 非加密配置
    base_url VARCHAR(500),
    model_mappings JSONB, -- 模型映射配置
    rate_limits JSONB, -- 速率限制设置
    retry_config JSONB, -- 重试配置
    timeout_config JSONB, -- 超时配置
    -- 状态和元数据
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'testing')),
    last_tested_at TIMESTAMP WITH TIME ZONE,
    test_result JSONB, -- 最后测试结果
    usage_statistics JSONB, -- 使用统计
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),
    updated_by UUID REFERENCES users(user_id),
    UNIQUE(tenant_id, provider_name, display_name)
);

-- 供应商模型配置表
CREATE TABLE ai_models (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID NOT NULL REFERENCES ai_provider_credentials(credential_id) ON DELETE CASCADE,
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

-- 索引
CREATE INDEX idx_ai_provider_credentials_tenant_id ON ai_provider_credentials(tenant_id);
CREATE INDEX idx_ai_provider_credentials_status ON ai_provider_credentials(status);
CREATE INDEX idx_ai_models_credential_id ON ai_models(credential_id);
CREATE INDEX idx_ai_models_type ON ai_models(model_type);
```

#### 2.2.3 会话管理表
```sql
-- 会话表
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(500),
    summary TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    metadata JSONB, -- 会话元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 消息表
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    parent_message_id UUID REFERENCES messages(message_id), -- 支持消息树结构
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- 'text', 'markdown', 'json'
    metadata JSONB, -- 消息元数据（模型信息、token使用量等）
    attachments JSONB, -- 附件信息
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 索引
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### 2.3 共享数据库 (shared_db)

#### 2.3.1 审计日志表
```sql
-- 审计日志表
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL, -- 必需的租户隔离字段
    user_id UUID, -- 可选，系统操作可能没有用户
    session_id UUID, -- 会话标识
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL, -- 'auth', 'api', 'admin', 'system'
    resource_type VARCHAR(100),
    resource_id UUID,
    action VARCHAR(100) NOT NULL,
    result VARCHAR(20) NOT NULL CHECK (result IN ('success', 'failure', 'error')),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 分区表（按月分区）
CREATE TABLE audit_logs_y2025m01 PARTITION OF audit_logs
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 索引
CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_tenant_created ON audit_logs(tenant_id, created_at);
```

#### 2.3.2 使用统计表
```sql
-- API调用统计
CREATE TABLE api_usage_stats (
    stat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    api_endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_partition DATE GENERATED ALWAYS AS (created_at::DATE) STORED
);

-- AI模型使用统计
CREATE TABLE ai_model_usage_stats (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    conversation_id UUID,
    message_id UUID,
    provider_name VARCHAR(100) NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd DECIMAL(10, 6),
    response_time_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_partition DATE GENERATED ALWAYS AS (created_at::DATE) STORED
);

-- 分区表
CREATE TABLE api_usage_stats_y2025m01 PARTITION OF api_usage_stats
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE ai_model_usage_stats_y2025m01 PARTITION OF ai_model_usage_stats
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 索引
CREATE INDEX idx_api_usage_stats_tenant_date ON api_usage_stats(tenant_id, date_partition);
CREATE INDEX idx_ai_model_usage_stats_tenant_date ON ai_model_usage_stats(tenant_id, date_partition);
CREATE INDEX idx_ai_model_usage_stats_user_date ON ai_model_usage_stats(user_id, date_partition);
```

## 3. 数据安全与加密

### 3.1 加密策略
```sql
-- 创建加密函数
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT, key_id TEXT)
RETURNS BYTEA AS $$
BEGIN
    -- 使用 pgcrypto 进行对称加密
    RETURN pgp_sym_encrypt(data, current_setting('app.encryption_key_' || key_id));
END;
$$ LANGUAGE plpgsql;

-- 创建解密函数
CREATE OR REPLACE FUNCTION decrypt_sensitive_data(encrypted_data BYTEA, key_id TEXT)
RETURNS TEXT AS $$
BEGIN
    -- 使用 pgcrypto 进行对称解密
    RETURN pgp_sym_decrypt(encrypted_data, current_setting('app.encryption_key_' || key_id));
END;
$$ LANGUAGE plpgsql;
```

### 3.2 访问控制
```sql
-- 创建租户特定角色
CREATE ROLE tenant_app_user;
GRANT CONNECT ON DATABASE tenant_db TO tenant_app_user;
GRANT USAGE ON SCHEMA public TO tenant_app_user;

-- 行级安全策略
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_tenant_isolation ON users
    FOR ALL TO tenant_app_user
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- 审计日志访问策略
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_logs_tenant_isolation ON audit_logs
    FOR ALL TO tenant_app_user
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

## 4. 性能优化

### 4.1 索引策略
```sql
-- 复合索引用于常见查询
CREATE INDEX idx_messages_conversation_user_created ON messages(conversation_id, user_id, created_at);
CREATE INDEX idx_usage_stats_tenant_user_date ON ai_model_usage_stats(tenant_id, user_id, date_partition);

-- 部分索引用于特定条件
CREATE INDEX idx_users_active_email ON users(email) WHERE status = 'active';
CREATE INDEX idx_conversations_active_updated ON conversations(updated_at) WHERE status = 'active';
```

### 4.2 查询优化
```sql
-- 创建物化视图用于统计查询
CREATE MATERIALIZED VIEW daily_usage_summary AS
SELECT 
    tenant_id,
    user_id,
    date_partition,
    COUNT(*) as total_calls,
    SUM(total_tokens) as total_tokens,
    SUM(estimated_cost_usd) as total_cost,
    AVG(response_time_ms) as avg_response_time
FROM ai_model_usage_stats
GROUP BY tenant_id, user_id, date_partition;

-- 创建刷新策略
CREATE INDEX idx_daily_usage_summary_tenant_date ON daily_usage_summary(tenant_id, date_partition);
```

## 5. 数据维护

### 5.1 清理策略
```sql
-- 清理过期的审计日志（保留2年）
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_logs 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '2 years';
END;
$$ LANGUAGE plpgsql;

-- 清理过期的使用统计（保留1年）
CREATE OR REPLACE FUNCTION cleanup_old_usage_stats()
RETURNS void AS $$
BEGIN
    DELETE FROM api_usage_stats 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 year';
    
    DELETE FROM ai_model_usage_stats 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;
```

### 5.2 备份策略
```sql
-- 创建备份函数
CREATE OR REPLACE FUNCTION backup_tenant_data(tenant_uuid UUID)
RETURNS void AS $$
BEGIN
    -- 执行租户数据备份逻辑
    PERFORM pg_dump_tenant_data(tenant_uuid);
END;
$$ LANGUAGE plpgsql;
```

## 6. 监控与维护

### 6.1 性能监控
```sql
-- 创建性能监控视图
CREATE VIEW database_performance_metrics AS
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_tup_hot_upd as hot_updates,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables;
```

### 6.2 健康检查
```sql
-- 数据库健康检查函数
CREATE OR REPLACE FUNCTION database_health_check()
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'timestamp', CURRENT_TIMESTAMP,
        'database_size', pg_database_size(current_database()),
        'active_connections', (SELECT count(*) FROM pg_stat_activity),
        'cache_hit_ratio', (SELECT round(sum(blks_hit)*100/sum(blks_hit+blks_read), 2) FROM pg_stat_database),
        'longest_query_duration', (SELECT max(extract(epoch from now() - query_start)) FROM pg_stat_activity WHERE state = 'active'),
        'table_bloat_check', (SELECT count(*) FROM pg_stat_user_tables WHERE n_dead_tup > n_live_tup * 0.1)
    ) INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

这个数据库设计文档提供了完整的数据库架构，包括多租户策略、安全加密、性能优化和维护方案。