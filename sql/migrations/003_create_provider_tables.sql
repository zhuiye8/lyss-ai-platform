-- =====================================================
-- Lyss Provider Service 数据库初始化脚本
-- 创建供应商服务相关的所有表结构
-- 
-- 作者: Lyss AI Team
-- 创建时间: 2025-01-21
-- 修改时间: 2025-01-21
-- =====================================================

-- 切换到供应商服务数据库
\c lyss_provider_db;

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =====================================================
-- 1. 供应商配置表
-- =====================================================
CREATE TABLE provider_configs (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    base_url VARCHAR(500) NOT NULL,
    auth_type VARCHAR(20) NOT NULL DEFAULT 'api_key',
    supported_models JSONB NOT NULL DEFAULT '[]',
    default_config JSONB DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_provider_status CHECK (status IN ('active', 'inactive', 'disabled')),
    CONSTRAINT chk_auth_type CHECK (auth_type IN ('api_key', 'oauth', 'basic_auth', 'bearer_token'))
);

-- 创建索引
CREATE INDEX idx_provider_configs_provider_id ON provider_configs(provider_id);
CREATE INDEX idx_provider_configs_status ON provider_configs(status);
CREATE INDEX idx_provider_configs_updated ON provider_configs(updated_at);

-- 添加注释
COMMENT ON TABLE provider_configs IS '供应商配置表，存储所有支持的AI供应商基础配置';
COMMENT ON COLUMN provider_configs.provider_id IS '供应商唯一标识符，如：openai、anthropic、google';
COMMENT ON COLUMN provider_configs.name IS '供应商显示名称';
COMMENT ON COLUMN provider_configs.description IS '供应商描述信息';
COMMENT ON COLUMN provider_configs.base_url IS '供应商API基础URL地址';
COMMENT ON COLUMN provider_configs.auth_type IS '认证类型：api_key、oauth、basic_auth、bearer_token';
COMMENT ON COLUMN provider_configs.supported_models IS '支持的模型列表JSON数组';
COMMENT ON COLUMN provider_configs.default_config IS '默认配置信息JSON对象';
COMMENT ON COLUMN provider_configs.status IS '状态：active-活跃、inactive-非活跃、disabled-禁用';

-- =====================================================
-- 2. Channel配置表
-- =====================================================
CREATE TABLE provider_channels (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    provider_id VARCHAR(50) NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    credentials TEXT NOT NULL, -- 加密存储
    models JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    priority INTEGER NOT NULL DEFAULT 1,
    weight INTEGER NOT NULL DEFAULT 100,
    max_requests_per_minute INTEGER NOT NULL DEFAULT 1000,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_channel_status CHECK (status IN ('active', 'inactive', 'disabled')),
    CONSTRAINT chk_channel_priority CHECK (priority >= 0 AND priority <= 100),
    CONSTRAINT chk_channel_weight CHECK (weight >= 1 AND weight <= 1000),
    CONSTRAINT chk_max_requests CHECK (max_requests_per_minute >= 1),
    CONSTRAINT uk_tenant_channel_name UNIQUE (tenant_id, name),
    
    -- 外键约束
    CONSTRAINT fk_channel_provider FOREIGN KEY (provider_id) REFERENCES provider_configs(provider_id)
);

-- 创建索引
CREATE INDEX idx_channels_tenant_id ON provider_channels(tenant_id);
CREATE INDEX idx_channels_provider_id ON provider_channels(provider_id);
CREATE INDEX idx_channels_status ON provider_channels(status);
CREATE INDEX idx_channels_priority ON provider_channels(priority DESC);
CREATE INDEX idx_channels_tenant_provider ON provider_channels(tenant_id, provider_id);
CREATE INDEX idx_channels_status_priority ON provider_channels(status, priority DESC);

-- 添加注释
COMMENT ON TABLE provider_channels IS 'Channel配置表，每个租户可配置多个Channel';
COMMENT ON COLUMN provider_channels.tenant_id IS '租户UUID，用于多租户隔离';
COMMENT ON COLUMN provider_channels.name IS 'Channel显示名称，租户内唯一';
COMMENT ON COLUMN provider_channels.provider_id IS '关联的供应商ID';
COMMENT ON COLUMN provider_channels.base_url IS 'Channel专用API地址，可覆盖默认地址';
COMMENT ON COLUMN provider_channels.credentials IS '加密存储的API凭证信息';
COMMENT ON COLUMN provider_channels.models IS '该Channel支持的模型列表';
COMMENT ON COLUMN provider_channels.status IS 'Channel状态';
COMMENT ON COLUMN provider_channels.priority IS '优先级，数字越小优先级越高';
COMMENT ON COLUMN provider_channels.weight IS '负载均衡权重，用于加权随机选择';
COMMENT ON COLUMN provider_channels.max_requests_per_minute IS '每分钟最大请求数限制';
COMMENT ON COLUMN provider_channels.config IS 'Channel额外配置信息';

-- =====================================================
-- 3. 请求日志表
-- =====================================================
CREATE TABLE proxy_request_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    channel_id INTEGER NOT NULL,
    provider_id VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    request_id VARCHAR(100),
    method VARCHAR(10) NOT NULL DEFAULT 'POST',
    endpoint VARCHAR(200) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time DECIMAL(8,2) NOT NULL, -- 毫秒，保留2位小数
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    is_stream BOOLEAN DEFAULT FALSE,
    client_ip INET,
    user_agent TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_response_time CHECK (response_time >= 0),
    CONSTRAINT chk_status_code CHECK (status_code >= 100 AND status_code <= 599),
    CONSTRAINT chk_tokens CHECK (prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0),
    
    -- 外键约束
    CONSTRAINT fk_request_logs_channel FOREIGN KEY (channel_id) REFERENCES provider_channels(id) ON DELETE CASCADE
);

-- 创建分区表索引（优化查询性能）
CREATE INDEX idx_request_logs_tenant_created ON proxy_request_logs(tenant_id, created_at DESC);
CREATE INDEX idx_request_logs_channel_created ON proxy_request_logs(channel_id, created_at DESC);
CREATE INDEX idx_request_logs_provider_created ON proxy_request_logs(provider_id, created_at DESC);
CREATE INDEX idx_request_logs_model ON proxy_request_logs(model);
CREATE INDEX idx_request_logs_status ON proxy_request_logs(status_code);
CREATE INDEX idx_request_logs_request_id ON proxy_request_logs(request_id) WHERE request_id IS NOT NULL;
CREATE INDEX idx_request_logs_created_only ON proxy_request_logs(created_at DESC);

-- 添加注释
COMMENT ON TABLE proxy_request_logs IS 'API代理请求日志表，记录所有代理请求详情';
COMMENT ON COLUMN proxy_request_logs.tenant_id IS '租户ID';
COMMENT ON COLUMN proxy_request_logs.channel_id IS '使用的Channel ID';
COMMENT ON COLUMN proxy_request_logs.provider_id IS '实际供应商ID';
COMMENT ON COLUMN proxy_request_logs.model IS '使用的AI模型';
COMMENT ON COLUMN proxy_request_logs.request_id IS '请求追踪ID';
COMMENT ON COLUMN proxy_request_logs.method IS 'HTTP请求方法';
COMMENT ON COLUMN proxy_request_logs.endpoint IS '请求的API端点';
COMMENT ON COLUMN proxy_request_logs.status_code IS 'HTTP响应状态码';
COMMENT ON COLUMN proxy_request_logs.response_time IS '请求响应时间，单位毫秒';
COMMENT ON COLUMN proxy_request_logs.prompt_tokens IS '输入Token数量';
COMMENT ON COLUMN proxy_request_logs.completion_tokens IS '输出Token数量';
COMMENT ON COLUMN proxy_request_logs.total_tokens IS '总Token数量';
COMMENT ON COLUMN proxy_request_logs.is_stream IS '是否为流式请求';
COMMENT ON COLUMN proxy_request_logs.client_ip IS '客户端IP地址';
COMMENT ON COLUMN proxy_request_logs.user_agent IS '客户端User-Agent';
COMMENT ON COLUMN proxy_request_logs.error_message IS '错误信息';

-- =====================================================
-- 4. Channel性能指标表
-- =====================================================
CREATE TABLE channel_metrics (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER NOT NULL UNIQUE,
    total_requests BIGINT DEFAULT 0,
    successful_requests BIGINT DEFAULT 0,
    failed_requests BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    avg_response_time DECIMAL(8,2) DEFAULT 0.0,
    success_rate DECIMAL(5,4) DEFAULT 0.0, -- 成功率，4位小数
    requests_per_minute DECIMAL(8,2) DEFAULT 0.0,
    last_request_time TIMESTAMP WITH TIME ZONE,
    last_success_time TIMESTAMP WITH TIME ZONE,
    last_error_time TIMESTAMP WITH TIME ZONE,
    health_status VARCHAR(20) DEFAULT 'unknown',
    health_check_time TIMESTAMP WITH TIME ZONE,
    consecutive_failures INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_metrics_positive CHECK (
        total_requests >= 0 AND successful_requests >= 0 AND failed_requests >= 0 AND 
        total_tokens >= 0 AND avg_response_time >= 0 AND success_rate >= 0 AND success_rate <= 1
    ),
    CONSTRAINT chk_health_status CHECK (health_status IN ('healthy', 'unhealthy', 'unknown', 'checking')),
    CONSTRAINT chk_consecutive_failures CHECK (consecutive_failures >= 0),
    
    -- 外键约束
    CONSTRAINT fk_metrics_channel FOREIGN KEY (channel_id) REFERENCES provider_channels(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_metrics_channel ON channel_metrics(channel_id);
CREATE INDEX idx_metrics_health ON channel_metrics(health_status);
CREATE INDEX idx_metrics_updated ON channel_metrics(updated_at);
CREATE INDEX idx_metrics_success_rate ON channel_metrics(success_rate DESC);

-- 添加注释
COMMENT ON TABLE channel_metrics IS 'Channel性能指标表，存储实时性能统计';
COMMENT ON COLUMN channel_metrics.channel_id IS 'Channel ID，与provider_channels表关联';
COMMENT ON COLUMN channel_metrics.total_requests IS '总请求数';
COMMENT ON COLUMN channel_metrics.successful_requests IS '成功请求数';
COMMENT ON COLUMN channel_metrics.failed_requests IS '失败请求数';
COMMENT ON COLUMN channel_metrics.total_tokens IS '总Token使用量';
COMMENT ON COLUMN channel_metrics.avg_response_time IS '平均响应时间，单位毫秒';
COMMENT ON COLUMN channel_metrics.success_rate IS '成功率，0-1之间的小数';
COMMENT ON COLUMN channel_metrics.requests_per_minute IS '每分钟请求数';
COMMENT ON COLUMN channel_metrics.health_status IS '健康状态：healthy-健康、unhealthy-不健康、unknown-未知、checking-检查中';
COMMENT ON COLUMN channel_metrics.consecutive_failures IS '连续失败次数';

-- =====================================================
-- 5. 租户配额管理表
-- =====================================================
CREATE TABLE tenant_quotas (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL UNIQUE,
    daily_request_limit INTEGER DEFAULT 10000,
    daily_token_limit BIGINT DEFAULT 1000000,
    daily_requests_used INTEGER DEFAULT 0,
    daily_tokens_used BIGINT DEFAULT 0,
    monthly_request_limit INTEGER DEFAULT 300000,
    monthly_token_limit BIGINT DEFAULT 30000000,
    monthly_requests_used INTEGER DEFAULT 0,
    monthly_tokens_used BIGINT DEFAULT 0,
    reset_date DATE DEFAULT CURRENT_DATE,
    monthly_reset_date DATE DEFAULT DATE_TRUNC('month', CURRENT_DATE),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_quota_limits CHECK (
        daily_request_limit >= 0 AND daily_token_limit >= 0 AND
        daily_requests_used >= 0 AND daily_tokens_used >= 0 AND
        monthly_request_limit >= 0 AND monthly_token_limit >= 0 AND
        monthly_requests_used >= 0 AND monthly_tokens_used >= 0
    ),
    CONSTRAINT chk_quota_status CHECK (status IN ('active', 'suspended', 'disabled'))
);

-- 创建索引
CREATE INDEX idx_quotas_tenant ON tenant_quotas(tenant_id);
CREATE INDEX idx_quotas_status ON tenant_quotas(status);
CREATE INDEX idx_quotas_reset_date ON tenant_quotas(reset_date);
CREATE INDEX idx_quotas_monthly_reset ON tenant_quotas(monthly_reset_date);

-- 添加注释
COMMENT ON TABLE tenant_quotas IS '租户配额管理表，控制租户API使用限额';
COMMENT ON COLUMN tenant_quotas.tenant_id IS '租户UUID';
COMMENT ON COLUMN tenant_quotas.daily_request_limit IS '每日请求限制';
COMMENT ON COLUMN tenant_quotas.daily_token_limit IS '每日Token限制';
COMMENT ON COLUMN tenant_quotas.daily_requests_used IS '每日已使用请求数';
COMMENT ON COLUMN tenant_quotas.daily_tokens_used IS '每日已使用Token数';
COMMENT ON COLUMN tenant_quotas.reset_date IS '每日配额重置日期';
COMMENT ON COLUMN tenant_quotas.status IS '配额状态：active-活跃、suspended-暂停、disabled-禁用';

-- =====================================================
-- 6. 创建触发器函数（自动更新updated_at字段）
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表创建更新时间触发器
CREATE TRIGGER update_provider_configs_updated_at BEFORE UPDATE ON provider_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channels_updated_at BEFORE UPDATE ON provider_channels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metrics_updated_at BEFORE UPDATE ON channel_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_quotas_updated_at BEFORE UPDATE ON tenant_quotas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 7. 创建视图（便于查询）
-- =====================================================

-- Channel详情视图
CREATE VIEW v_channel_details AS
SELECT 
    c.id,
    c.tenant_id,
    c.name,
    c.provider_id,
    p.name AS provider_name,
    c.base_url,
    c.models,
    c.status,
    c.priority,
    c.weight,
    c.max_requests_per_minute,
    c.created_at,
    c.updated_at,
    COALESCE(m.health_status, 'unknown') AS health_status,
    COALESCE(m.total_requests, 0) AS total_requests,
    COALESCE(m.success_rate, 0) AS success_rate,
    COALESCE(m.avg_response_time, 0) AS avg_response_time,
    m.last_request_time,
    m.last_success_time,
    m.last_error_time
FROM provider_channels c
LEFT JOIN provider_configs p ON c.provider_id = p.provider_id
LEFT JOIN channel_metrics m ON c.id = m.channel_id;

COMMENT ON VIEW v_channel_details IS 'Channel详情视图，包含供应商信息和性能指标';

-- 租户使用统计视图
CREATE VIEW v_tenant_usage_stats AS
SELECT 
    rl.tenant_id,
    DATE(rl.created_at) AS usage_date,
    COUNT(*) AS total_requests,
    COUNT(*) FILTER (WHERE rl.status_code >= 200 AND rl.status_code < 300) AS successful_requests,
    COUNT(*) FILTER (WHERE rl.status_code >= 400) AS failed_requests,
    SUM(rl.total_tokens) AS total_tokens,
    AVG(rl.response_time) AS avg_response_time,
    COUNT(DISTINCT rl.channel_id) AS channels_used,
    COUNT(DISTINCT rl.model) AS models_used
FROM proxy_request_logs rl
GROUP BY rl.tenant_id, DATE(rl.created_at);

COMMENT ON VIEW v_tenant_usage_stats IS '租户使用统计视图，按日期聚合';

-- 供应商使用统计视图
CREATE VIEW v_provider_usage_stats AS
SELECT 
    rl.provider_id,
    p.name AS provider_name,
    DATE(rl.created_at) AS usage_date,
    COUNT(*) AS total_requests,
    COUNT(*) FILTER (WHERE rl.status_code >= 200 AND rl.status_code < 300) AS successful_requests,
    SUM(rl.total_tokens) AS total_tokens,
    AVG(rl.response_time) AS avg_response_time,
    COUNT(DISTINCT rl.tenant_id) AS tenants_count,
    COUNT(DISTINCT rl.channel_id) AS channels_count
FROM proxy_request_logs rl
LEFT JOIN provider_configs p ON rl.provider_id = p.provider_id
GROUP BY rl.provider_id, p.name, DATE(rl.created_at);

COMMENT ON VIEW v_provider_usage_stats IS '供应商使用统计视图，按日期聚合';

-- =====================================================
-- 8. 创建基础数据清理函数
-- =====================================================

-- 清理老旧日志的函数（保留30天）
CREATE OR REPLACE FUNCTION cleanup_old_request_logs(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    cutoff_date := NOW() - INTERVAL '1 day' * retention_days;
    
    DELETE FROM proxy_request_logs 
    WHERE created_at < cutoff_date;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- 记录清理操作
    RAISE NOTICE '清理了 % 条 % 天前的请求日志', deleted_count, retention_days;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_request_logs IS '清理指定天数前的请求日志，默认保留30天';

-- 重置每日配额的函数
CREATE OR REPLACE FUNCTION reset_daily_quotas()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE tenant_quotas 
    SET daily_requests_used = 0,
        daily_tokens_used = 0,
        reset_date = CURRENT_DATE
    WHERE reset_date < CURRENT_DATE;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RAISE NOTICE '重置了 % 个租户的每日配额', updated_count;
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reset_daily_quotas IS '重置所有租户的每日配额';

-- =====================================================
-- 9. 创建性能优化函数
-- =====================================================

-- 更新Channel指标的函数
CREATE OR REPLACE FUNCTION update_channel_metrics(p_channel_id INTEGER)
RETURNS VOID AS $$
DECLARE
    v_total_requests BIGINT;
    v_successful_requests BIGINT;
    v_failed_requests BIGINT;
    v_total_tokens BIGINT;
    v_avg_response_time DECIMAL(8,2);
    v_success_rate DECIMAL(5,4);
    v_last_request_time TIMESTAMP WITH TIME ZONE;
    v_last_success_time TIMESTAMP WITH TIME ZONE;
    v_last_error_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- 计算统计数据（过去24小时）
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 300),
        COUNT(*) FILTER (WHERE status_code >= 400),
        COALESCE(SUM(total_tokens), 0),
        COALESCE(AVG(response_time), 0),
        MAX(created_at),
        MAX(created_at) FILTER (WHERE status_code >= 200 AND status_code < 300),
        MAX(created_at) FILTER (WHERE status_code >= 400)
    INTO v_total_requests, v_successful_requests, v_failed_requests, 
         v_total_tokens, v_avg_response_time, v_last_request_time,
         v_last_success_time, v_last_error_time
    FROM proxy_request_logs
    WHERE channel_id = p_channel_id 
      AND created_at >= NOW() - INTERVAL '24 hours';
    
    -- 计算成功率
    IF v_total_requests > 0 THEN
        v_success_rate := v_successful_requests::DECIMAL / v_total_requests;
    ELSE
        v_success_rate := 0;
    END IF;
    
    -- 更新或插入指标
    INSERT INTO channel_metrics (
        channel_id, total_requests, successful_requests, failed_requests,
        total_tokens, avg_response_time, success_rate,
        last_request_time, last_success_time, last_error_time
    ) VALUES (
        p_channel_id, v_total_requests, v_successful_requests, v_failed_requests,
        v_total_tokens, v_avg_response_time, v_success_rate,
        v_last_request_time, v_last_success_time, v_last_error_time
    )
    ON CONFLICT (channel_id) DO UPDATE SET
        total_requests = EXCLUDED.total_requests,
        successful_requests = EXCLUDED.successful_requests,
        failed_requests = EXCLUDED.failed_requests,
        total_tokens = EXCLUDED.total_tokens,
        avg_response_time = EXCLUDED.avg_response_time,
        success_rate = EXCLUDED.success_rate,
        last_request_time = EXCLUDED.last_request_time,
        last_success_time = EXCLUDED.last_success_time,
        last_error_time = EXCLUDED.last_error_time,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_channel_metrics IS '更新指定Channel的性能指标（基于过去24小时数据）';

-- =====================================================
-- 10. 初始化基础数据
-- =====================================================

-- 插入预定义的供应商配置
INSERT INTO provider_configs (provider_id, name, description, base_url, auth_type, supported_models, default_config) VALUES
('openai', 'OpenAI', 'OpenAI GPT系列模型', 'https://api.openai.com/v1', 'api_key', 
 '["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]',
 '{"timeout": 30, "max_retries": 3}'),
 
('anthropic', 'Anthropic', 'Anthropic Claude系列模型', 'https://api.anthropic.com', 'api_key',
 '["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]',
 '{"timeout": 30, "max_retries": 3}'),
 
('google', 'Google AI', 'Google Gemini系列模型', 'https://generativelanguage.googleapis.com/v1beta', 'api_key',
 '["gemini-pro", "gemini-pro-vision", "gemini-ultra"]',
 '{"timeout": 30, "max_retries": 3}'),
 
('deepseek', 'DeepSeek', 'DeepSeek AI系列模型', 'https://api.deepseek.com', 'api_key',
 '["deepseek-chat", "deepseek-coder"]',
 '{"timeout": 30, "max_retries": 3}'),
 
('azure-openai', 'Azure OpenAI', 'Microsoft Azure OpenAI服务', 'https://{resource}.openai.azure.com', 'api_key',
 '["gpt-35-turbo", "gpt-4", "gpt-4-32k"]',
 '{"api_version": "2024-02-15-preview", "timeout": 30}');

-- 输出初始化完成信息
SELECT 
    'Provider Service数据库初始化完成' AS status,
    COUNT(*) AS provider_count
FROM provider_configs;

-- 显示已创建的表
SELECT 
    schemaname,
    tablename,
    hasindexes,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename LIKE '%provider%' OR tablename LIKE '%channel%' OR tablename LIKE '%quota%'
ORDER BY tablename;