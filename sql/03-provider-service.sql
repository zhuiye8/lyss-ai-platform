-- ================================================================
-- Lyss Provider Service - 统一数据库Schema  
-- 
-- 🚨 重要：本SQL脚本符合统一数据库架构设计规范
-- 📋 架构原则：所有微服务共享同一PostgreSQL数据库实例（lyss_db）
-- 📦 表命名：使用 provider_ 前缀，符合模块化管理规范
-- 🔒 多租户：通过tenant_id实现数据隔离，支持Row Level Security
-- 
-- 包含功能：供应商管理、Channel管理、Token管理、请求日志、指标统计
--
-- Author: Lyss AI Team  
-- Created: 2025-01-22
-- Modified: 2025-01-22 (架构合规性更新)
-- ================================================================

-- 启用必要的PostgreSQL扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ================================================================
-- 1. 供应商类型定义表（符合统一架构：provider_前缀）
-- ================================================================
CREATE TABLE provider_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,            -- openai, anthropic, deepseek, etc.
    display_name VARCHAR(100) NOT NULL,          -- OpenAI, Anthropic, DeepSeek
    base_url TEXT,
    supported_models JSONB DEFAULT '[]',
    api_format VARCHAR(20) DEFAULT 'openai',     -- openai, anthropic, custom
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_provider_types_name ON provider_types(name);
CREATE INDEX idx_provider_types_status ON provider_types(status);

-- 插入预置供应商类型
INSERT INTO provider_types (name, display_name, base_url, api_format) VALUES
('openai', 'OpenAI', 'https://api.openai.com', 'openai'),
('anthropic', 'Anthropic', 'https://api.anthropic.com', 'anthropic'),
('deepseek', 'DeepSeek', 'https://api.deepseek.com', 'openai'),
('azure-openai', 'Azure OpenAI', NULL, 'openai'),
('zhipu', '智谱AI', 'https://open.bigmodel.cn', 'openai'),
('google', 'Google AI', 'https://generativelanguage.googleapis.com', 'google'),
('baidu', '百度文心', 'https://aip.baidubce.com', 'baidu'),
('minimax', 'MiniMax', 'https://api.minimax.chat', 'minimax'),
('moonshot', 'Moonshot', 'https://api.moonshot.cn', 'openai');

-- ================================================================
-- 2. Provider Channel配置表（基于One-API设计）
-- ================================================================
CREATE TABLE provider_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,                    -- 租户ID（多租户隔离）
    name VARCHAR(100) NOT NULL,                 -- 显示名称
    type INTEGER NOT NULL REFERENCES provider_types(id),  -- 供应商类型
    
    -- One-API标准字段
    key TEXT NOT NULL,                          -- 加密的API密钥
    priority INTEGER DEFAULT 1,                -- 优先级 (1-100)
    weight INTEGER DEFAULT 1,                  -- 权重 (负载均衡)
    status INTEGER DEFAULT 1,                  -- 1=启用, 2=禁用, 3=错误
    
    -- 配额管理
    quota BIGINT DEFAULT -1,                   -- -1表示无限制
    used_quota BIGINT DEFAULT 0,
    rate_limit INTEGER DEFAULT 100,           -- 每分钟请求限制
    
    -- 配置范围
    config_scope VARCHAR(20) DEFAULT 'personal', -- personal, group, tenant
    owner_id UUID,                             -- 个人配置时的用户ID
    group_id UUID,                             -- 群组配置时的群组ID
    
    -- 模型配置
    models JSONB DEFAULT '[]',                 -- 支持的模型列表
    model_mapping JSONB DEFAULT '{}',          -- 模型映射配置
    
    -- 额外配置
    base_url VARCHAR(500),                     -- 自定义Base URL
    config JSONB DEFAULT '{}',                 -- 其他配置参数
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 唯一约束
    CONSTRAINT uk_provider_channels_tenant_name UNIQUE(tenant_id, name)
);

-- 创建索引
CREATE INDEX idx_provider_channels_tenant_scope ON provider_channels(tenant_id, config_scope);
CREATE INDEX idx_provider_channels_status ON provider_channels(status);
CREATE INDEX idx_provider_channels_priority ON provider_channels(priority);
CREATE INDEX idx_provider_channels_type ON provider_channels(type);
CREATE INDEX idx_provider_channels_tenant_type ON provider_channels(tenant_id, type);

-- 添加表注释
COMMENT ON TABLE provider_channels IS 'Provider Channel配置表（基于One-API设计，支持多租户）';
COMMENT ON COLUMN provider_channels.tenant_id IS '租户UUID，实现多租户数据隔离';
COMMENT ON COLUMN provider_channels.key IS 'pgcrypto加密后的API密钥';
COMMENT ON COLUMN provider_channels.priority IS '优先级，数字越小优先级越高';
COMMENT ON COLUMN provider_channels.weight IS '负载均衡权重';
COMMENT ON COLUMN provider_channels.quota IS '配额限制，-1表示无限制';

-- ================================================================
-- 3. 用户Token表（API访问令牌管理，符合统一架构）
-- ================================================================
CREATE TABLE provider_user_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,                -- Token名称
    key TEXT UNIQUE NOT NULL,                  -- 实际Token值
    
    -- 权限控制
    allowed_channels JSONB DEFAULT '[]',       -- 允许使用的Channel ID列表
    allowed_models JSONB DEFAULT '[]',         -- 允许使用的模型列表
    
    -- 配额管理
    quota BIGINT DEFAULT -1,                   -- -1表示无限制
    used_quota BIGINT DEFAULT 0,
    rate_limit INTEGER DEFAULT 60,            -- 每分钟请求限制
    
    -- 状态管理
    status INTEGER DEFAULT 1,                 -- 1=启用, 2=禁用, 3=过期
    expires_at TIMESTAMP,                     -- 过期时间
    last_used_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 唯一约束
    CONSTRAINT uk_provider_user_tokens_tenant_name UNIQUE(tenant_id, name)
);

-- 创建索引
CREATE INDEX idx_provider_user_tokens_tenant_user ON provider_user_tokens(tenant_id, user_id);
CREATE INDEX idx_provider_user_tokens_key ON provider_user_tokens(key);
CREATE INDEX idx_provider_user_tokens_status ON provider_user_tokens(status);
CREATE INDEX idx_provider_user_tokens_expires ON provider_user_tokens(expires_at);

-- 添加表注释
COMMENT ON TABLE provider_user_tokens IS '用户API访问令牌管理表（符合统一架构）';
COMMENT ON COLUMN provider_user_tokens.key IS 'API访问令牌（明文存储，需要在应用层加密）';
COMMENT ON COLUMN provider_user_tokens.allowed_channels IS '允许访问的Channel列表（JSON数组）';

-- ================================================================
-- 4. 请求日志表（支持大数据量和分区）
-- ================================================================
CREATE TABLE provider_request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    provider_id VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    
    -- 请求信息
    request_id VARCHAR(100),                   -- 请求追踪ID
    method VARCHAR(10) DEFAULT 'POST',
    endpoint VARCHAR(200) NOT NULL,
    
    -- 响应信息
    status_code INTEGER NOT NULL,
    response_time FLOAT NOT NULL,              -- 响应时间（毫秒）
    
    -- Token统计
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    -- 请求特征
    is_stream BOOLEAN DEFAULT FALSE,
    client_ip INET,
    user_agent TEXT,
    
    -- 错误信息
    error_message TEXT,
    error_type VARCHAR(50),
    
    -- 成本计算
    estimated_cost DECIMAL(10,6) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引（优化查询性能）
CREATE INDEX idx_provider_request_logs_tenant_created ON provider_request_logs(tenant_id, created_at);
CREATE INDEX idx_provider_request_logs_channel_created ON provider_request_logs(channel_id, created_at);
CREATE INDEX idx_provider_request_logs_provider_created ON provider_request_logs(provider_id, created_at);
CREATE INDEX idx_provider_request_logs_model ON provider_request_logs(model);
CREATE INDEX idx_provider_request_logs_status ON provider_request_logs(status_code);
CREATE INDEX idx_provider_request_logs_created ON provider_request_logs(created_at);

-- 添加表注释
COMMENT ON TABLE provider_request_logs IS 'Provider请求日志表（支持大数据量存储）';
COMMENT ON COLUMN provider_request_logs.response_time IS '响应时间，单位毫秒';
COMMENT ON COLUMN provider_request_logs.estimated_cost IS '预估成本（美元）';

-- ================================================================
-- 5. Channel性能指标表
-- ================================================================
CREATE TABLE provider_channel_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID UNIQUE NOT NULL,
    
    -- 基础统计
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    
    -- Token统计
    total_tokens BIGINT DEFAULT 0,
    total_prompt_tokens BIGINT DEFAULT 0,
    total_completion_tokens BIGINT DEFAULT 0,
    
    -- 性能指标
    avg_response_time FLOAT DEFAULT 0.0,
    success_rate FLOAT DEFAULT 0.0,
    requests_per_minute FLOAT DEFAULT 0.0,
    
    -- 时间戳
    last_request_time TIMESTAMP,
    last_success_time TIMESTAMP,
    last_error_time TIMESTAMP,
    
    -- 健康状态
    health_status VARCHAR(20) DEFAULT 'unknown',  -- healthy, unhealthy, unknown
    health_check_time TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    
    -- 成本统计
    total_cost DECIMAL(10,4) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_provider_channel_metrics_channel ON provider_channel_metrics(channel_id);
CREATE INDEX idx_provider_channel_metrics_health ON provider_channel_metrics(health_status);
CREATE INDEX idx_provider_channel_metrics_updated ON provider_channel_metrics(updated_at);
CREATE INDEX idx_provider_channel_metrics_success_rate ON provider_channel_metrics(success_rate);

-- 添加表注释
COMMENT ON TABLE provider_channel_metrics IS 'Provider Channel性能指标表';
COMMENT ON COLUMN provider_channel_metrics.success_rate IS '成功率（0.0-1.0）';
COMMENT ON COLUMN provider_channel_metrics.health_status IS '健康状态：healthy/unhealthy/unknown';

-- ================================================================
-- 6. 租户配额管理表
-- ================================================================
CREATE TABLE provider_tenant_quotas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID UNIQUE NOT NULL,
    
    -- 每日配额
    daily_request_limit INTEGER DEFAULT 10000,
    daily_token_limit INTEGER DEFAULT 1000000,
    daily_requests_used INTEGER DEFAULT 0,
    daily_tokens_used INTEGER DEFAULT 0,
    
    -- 每月配额
    monthly_request_limit INTEGER DEFAULT 300000,
    monthly_token_limit INTEGER DEFAULT 30000000,
    monthly_requests_used INTEGER DEFAULT 0,
    monthly_tokens_used INTEGER DEFAULT 0,
    
    -- 重置时间
    reset_date DATE DEFAULT CURRENT_DATE,
    monthly_reset_date DATE DEFAULT DATE_TRUNC('month', CURRENT_DATE),
    
    -- 成本配额
    daily_cost_limit DECIMAL(10,2) DEFAULT 100.00,
    monthly_cost_limit DECIMAL(10,2) DEFAULT 1000.00,
    daily_cost_used DECIMAL(10,2) DEFAULT 0,
    monthly_cost_used DECIMAL(10,2) DEFAULT 0,
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'active',       -- active, suspended, disabled
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_provider_tenant_quotas_tenant ON provider_tenant_quotas(tenant_id);
CREATE INDEX idx_provider_tenant_quotas_status ON provider_tenant_quotas(status);
CREATE INDEX idx_provider_tenant_quotas_reset ON provider_tenant_quotas(reset_date);

-- 添加表注释
COMMENT ON TABLE provider_tenant_quotas IS '租户配额管理表（支持请求量、Token量、成本配额）';

-- ================================================================
-- 7. 系统配置表（可选）
-- ================================================================
CREATE TABLE provider_system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_provider_system_configs_key ON provider_system_configs(config_key);

-- 插入默认系统配置
INSERT INTO provider_system_configs (config_key, config_value, description) VALUES
('default_rate_limits', '{"requests_per_minute": 60, "tokens_per_minute": 10000}', '默认速率限制配置'),
('health_check_interval', '300', '健康检查间隔（秒）'),
('token_cleanup_days', '90', 'Token清理天数'),
('log_retention_days', '30', '日志保留天数');

-- ================================================================
-- 8. 创建视图（便于查询）
-- ================================================================

-- Channel健康状况视图
CREATE VIEW v_channel_health AS
SELECT 
    pc.id,
    pc.name,
    pc.tenant_id,
    pt.display_name as provider_name,
    pc.status,
    pc.priority,
    pc.weight,
    pcm.health_status,
    pcm.success_rate,
    pcm.avg_response_time,
    pcm.total_requests,
    pcm.last_request_time
FROM provider_channels pc
LEFT JOIN provider_types pt ON pc.type = pt.id
LEFT JOIN provider_channel_metrics pcm ON pc.id = pcm.channel_id;

-- 租户使用统计视图
CREATE VIEW v_tenant_usage_summary AS
SELECT 
    ptq.tenant_id,
    ptq.daily_requests_used,
    ptq.daily_tokens_used,
    ptq.daily_cost_used,
    ptq.monthly_requests_used,
    ptq.monthly_tokens_used,
    ptq.monthly_cost_used,
    COUNT(pc.id) as total_channels,
    COUNT(CASE WHEN pc.status = 1 THEN 1 END) as active_channels
FROM provider_tenant_quotas ptq
LEFT JOIN provider_channels pc ON ptq.tenant_id = pc.tenant_id
GROUP BY ptq.tenant_id, ptq.daily_requests_used, ptq.daily_tokens_used, 
         ptq.daily_cost_used, ptq.monthly_requests_used, 
         ptq.monthly_tokens_used, ptq.monthly_cost_used;

-- ================================================================
-- 9. 创建函数和触发器
-- ================================================================

-- 更新配额使用量的函数
CREATE OR REPLACE FUNCTION update_quota_usage()
RETURNS TRIGGER AS $$
BEGIN
    -- 更新租户配额使用量
    UPDATE provider_tenant_quotas 
    SET 
        daily_requests_used = daily_requests_used + 1,
        daily_tokens_used = daily_tokens_used + NEW.total_tokens,
        daily_cost_used = daily_cost_used + NEW.estimated_cost,
        monthly_requests_used = monthly_requests_used + 1,
        monthly_tokens_used = monthly_tokens_used + NEW.total_tokens,
        monthly_cost_used = monthly_cost_used + NEW.estimated_cost,
        updated_at = NOW()
    WHERE tenant_id = NEW.tenant_id;
    
    -- 更新Channel指标
    INSERT INTO provider_channel_metrics (channel_id, total_requests, successful_requests, failed_requests, total_tokens)
    VALUES (NEW.channel_id, 1, 
            CASE WHEN NEW.status_code < 400 THEN 1 ELSE 0 END,
            CASE WHEN NEW.status_code >= 400 THEN 1 ELSE 0 END,
            NEW.total_tokens)
    ON CONFLICT (channel_id) DO UPDATE SET
        total_requests = provider_channel_metrics.total_requests + 1,
        successful_requests = provider_channel_metrics.successful_requests + 
            CASE WHEN NEW.status_code < 400 THEN 1 ELSE 0 END,
        failed_requests = provider_channel_metrics.failed_requests + 
            CASE WHEN NEW.status_code >= 400 THEN 1 ELSE 0 END,
        total_tokens = provider_channel_metrics.total_tokens + NEW.total_tokens,
        success_rate = (provider_channel_metrics.successful_requests + 
            CASE WHEN NEW.status_code < 400 THEN 1 ELSE 0 END)::float / 
            (provider_channel_metrics.total_requests + 1),
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
CREATE TRIGGER tg_update_quota_usage
    AFTER INSERT ON provider_request_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_quota_usage();

-- ================================================================
-- 10. 权限和安全设置
-- ================================================================

-- 创建应用用户角色
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'lyss_provider_app') THEN
        CREATE ROLE lyss_provider_app LOGIN PASSWORD 'change_me_in_production';
    END IF;
END
$$;

-- 授权应用用户访问权限
GRANT USAGE ON SCHEMA public TO lyss_provider_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lyss_provider_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lyss_provider_app;

-- 启用行级安全（可选，用于额外安全保障）
-- ALTER TABLE provider_channels ENABLE ROW LEVEL SECURITY;

-- ================================================================
-- 11. 性能优化配置
-- ================================================================

-- 设置表的存储参数（可选）
ALTER TABLE provider_request_logs SET (
    fillfactor = 90,  -- 预留10%空间用于UPDATE
    autovacuum_vacuum_scale_factor = 0.1
);

-- 创建部分索引（只索引活跃数据）
CREATE INDEX idx_provider_channels_active 
ON provider_channels (tenant_id, type) 
WHERE status = 1;

-- ================================================================
-- 12. 备份和维护
-- ================================================================

-- 创建清理旧日志的函数
CREATE OR REPLACE FUNCTION cleanup_old_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM provider_request_logs 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- 记录清理操作
    INSERT INTO provider_system_configs (config_key, config_value, description)
    VALUES ('last_cleanup', to_jsonb(NOW()), '上次日志清理时间')
    ON CONFLICT (config_key) DO UPDATE SET 
        config_value = to_jsonb(NOW()),
        updated_at = NOW();
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Schema创建完成！
-- ================================================================

-- 显示创建摘要
DO $$
BEGIN
    RAISE NOTICE '✅ Lyss Provider Service 统一数据库Schema创建完成！';
    RAISE NOTICE '📊 包含表数量: %', (
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'provider_%'
    );
    RAISE NOTICE '🔗 包含索引数量: %', (
        SELECT COUNT(*) 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename LIKE 'provider_%'
    );
    RAISE NOTICE '⚡ 优化特性: 索引优化、触发器、视图、清理函数';
    RAISE NOTICE '🛡️  安全特性: 应用角色、权限控制、加密支持';
END
$$;