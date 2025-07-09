-- Lyss AI Platform - 共享数据库表结构
-- 此脚本创建共享数据库的表结构，用于存储审计日志、使用统计等大容量数据

-- ===========================================
-- 1. 审计日志表（分区表）
-- ===========================================

-- 审计日志主表
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL, -- 租户隔离字段
    user_id UUID, -- 可选，系统操作可能没有用户
    session_id UUID, -- 会话标识
    
    -- 事件信息
    event_type VARCHAR(100) NOT NULL, -- 事件类型
    event_category VARCHAR(50) NOT NULL, -- 事件分类：'auth', 'api', 'admin', 'system'
    action VARCHAR(100) NOT NULL, -- 具体操作
    resource_type VARCHAR(100), -- 资源类型
    resource_id UUID, -- 资源ID
    
    -- 结果和详情
    result VARCHAR(20) NOT NULL CHECK (result IN ('success', 'failure', 'error')),
    details JSONB, -- 详细信息
    error_message TEXT, -- 错误信息
    
    -- 请求信息
    ip_address INET, -- 客户端IP
    user_agent TEXT, -- 用户代理
    request_id UUID, -- 请求ID
    api_endpoint VARCHAR(500), -- API端点
    http_method VARCHAR(10), -- HTTP方法
    
    -- 性能信息
    duration_ms INTEGER, -- 执行时间（毫秒）
    
    -- 时间戳
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    PRIMARY KEY (log_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 创建月份分区表（2025年）
CREATE TABLE IF NOT EXISTS audit_logs_2025_01 PARTITION OF audit_logs
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_02 PARTITION OF audit_logs
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_03 PARTITION OF audit_logs
FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_04 PARTITION OF audit_logs
FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_05 PARTITION OF audit_logs
FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_06 PARTITION OF audit_logs
FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_07 PARTITION OF audit_logs
FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_08 PARTITION OF audit_logs
FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_09 PARTITION OF audit_logs
FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_10 PARTITION OF audit_logs
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_11 PARTITION OF audit_logs
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS audit_logs_2025_12 PARTITION OF audit_logs
FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- ===========================================
-- 2. 使用统计表
-- ===========================================

-- API使用统计表
CREATE TABLE IF NOT EXISTS api_usage_stats (
    usage_id UUID DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    
    -- API信息
    api_endpoint VARCHAR(500) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    api_version VARCHAR(20),
    
    -- 响应信息
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    
    -- 用户信息
    ip_address INET,
    user_agent TEXT,
    
    -- 时间戳
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    date_partition DATE,
    
    PRIMARY KEY (usage_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- AI模型使用统计表
CREATE TABLE IF NOT EXISTS ai_model_usage_stats (
    usage_id UUID DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    conversation_id UUID,
    message_id UUID,
    
    -- 模型信息
    provider_name VARCHAR(100) NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    model_type VARCHAR(50), -- 'chat', 'completion', 'embedding', 'image'
    
    -- Token使用统计
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- 成本信息
    estimated_cost_usd DECIMAL(10, 8) DEFAULT 0.00000000,
    pricing_model VARCHAR(50), -- 'per_token', 'per_request', 'per_minute'
    
    -- 性能信息
    response_time_ms INTEGER,
    queue_time_ms INTEGER,
    processing_time_ms INTEGER,
    
    -- 结果信息
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_type VARCHAR(100),
    error_message TEXT,
    
    -- 模型配置
    model_config JSONB, -- 温度、top_p等参数
    
    -- 时间戳
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    date_partition DATE,
    
    PRIMARY KEY (usage_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 创建使用统计月份分区表
CREATE TABLE IF NOT EXISTS api_usage_stats_2025_01 PARTITION OF api_usage_stats
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS ai_model_usage_stats_2025_01 PARTITION OF ai_model_usage_stats
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- ===========================================
-- 3. 性能监控表
-- ===========================================

-- 系统性能指标表
CREATE TABLE IF NOT EXISTS system_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    
    -- 指标信息
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'counter', 'gauge', 'histogram'
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit VARCHAR(20), -- 'ms', 'bytes', 'requests', 'percent'
    
    -- 标签和维度
    labels JSONB, -- 指标标签
    dimensions JSONB, -- 维度信息
    
    -- 时间戳
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 数据库性能指标表
CREATE TABLE IF NOT EXISTS database_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    
    -- 数据库信息
    database_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    query_type VARCHAR(50), -- 'SELECT', 'INSERT', 'UPDATE', 'DELETE'
    
    -- 性能指标
    execution_time_ms DOUBLE PRECISION,
    rows_affected INTEGER,
    cpu_usage_percent DOUBLE PRECISION,
    memory_usage_bytes BIGINT,
    io_read_bytes BIGINT,
    io_write_bytes BIGINT,
    
    -- 查询信息
    query_hash VARCHAR(64), -- 查询的哈希值
    query_text TEXT, -- 查询文本（可选）
    
    -- 时间戳
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ===========================================
-- 4. 索引创建
-- ===========================================

-- 审计日志索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_category ON audit_logs(event_category);
CREATE INDEX IF NOT EXISTS idx_audit_logs_result ON audit_logs(result);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_timestamp ON audit_logs(tenant_id, timestamp);

-- API使用统计索引
CREATE INDEX IF NOT EXISTS idx_api_usage_stats_tenant_date ON api_usage_stats(tenant_id, date_partition);
CREATE INDEX IF NOT EXISTS idx_api_usage_stats_user_date ON api_usage_stats(user_id, date_partition);
CREATE INDEX IF NOT EXISTS idx_api_usage_stats_endpoint ON api_usage_stats(api_endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_stats_status ON api_usage_stats(status_code);

-- AI模型使用统计索引
CREATE INDEX IF NOT EXISTS idx_ai_model_usage_stats_tenant_date ON ai_model_usage_stats(tenant_id, date_partition);
CREATE INDEX IF NOT EXISTS idx_ai_model_usage_stats_user_date ON ai_model_usage_stats(user_id, date_partition);
CREATE INDEX IF NOT EXISTS idx_ai_model_usage_stats_provider ON ai_model_usage_stats(provider_name);
CREATE INDEX IF NOT EXISTS idx_ai_model_usage_stats_model ON ai_model_usage_stats(model_name);
CREATE INDEX IF NOT EXISTS idx_ai_model_usage_stats_conversation ON ai_model_usage_stats(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_model_usage_stats_success ON ai_model_usage_stats(success);

-- 性能监控索引
CREATE INDEX IF NOT EXISTS idx_system_performance_metrics_tenant_name ON system_performance_metrics(tenant_id, metric_name);
CREATE INDEX IF NOT EXISTS idx_system_performance_metrics_timestamp ON system_performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_database_performance_metrics_tenant_db ON database_performance_metrics(tenant_id, database_name);
CREATE INDEX IF NOT EXISTS idx_database_performance_metrics_timestamp ON database_performance_metrics(timestamp);

-- ===========================================
-- 5. 物化视图（用于统计查询）
-- ===========================================

-- 日使用统计汇总视图
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_usage_summary AS
SELECT 
    tenant_id,
    user_id,
    date_partition,
    COUNT(*) as total_api_calls,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_calls,
    SUM(total_tokens) as total_tokens,
    SUM(estimated_cost_usd) as total_cost_usd,
    AVG(response_time_ms) as avg_response_time_ms,
    MIN(response_time_ms) as min_response_time_ms,
    MAX(response_time_ms) as max_response_time_ms,
    COUNT(DISTINCT provider_name) as unique_providers,
    COUNT(DISTINCT model_name) as unique_models
FROM ai_model_usage_stats
GROUP BY tenant_id, user_id, date_partition;

-- 月使用统计汇总视图
CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_usage_summary AS
SELECT 
    tenant_id,
    user_id,
    DATE_TRUNC('month', date_partition) as month,
    COUNT(*) as total_api_calls,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_calls,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_calls,
    SUM(total_tokens) as total_tokens,
    SUM(estimated_cost_usd) as total_cost_usd,
    AVG(response_time_ms) as avg_response_time_ms
FROM ai_model_usage_stats
GROUP BY tenant_id, user_id, DATE_TRUNC('month', date_partition);

-- 为物化视图创建索引
CREATE INDEX IF NOT EXISTS idx_daily_usage_summary_tenant_date ON daily_usage_summary(tenant_id, date_partition);
CREATE INDEX IF NOT EXISTS idx_daily_usage_summary_user_date ON daily_usage_summary(user_id, date_partition);
CREATE INDEX IF NOT EXISTS idx_monthly_usage_summary_tenant_month ON monthly_usage_summary(tenant_id, month);
CREATE INDEX IF NOT EXISTS idx_monthly_usage_summary_user_month ON monthly_usage_summary(user_id, month);

-- ===========================================
-- 6. 触发器函数
-- ===========================================

-- 设置date_partition字段的触发器函数
CREATE OR REPLACE FUNCTION set_date_partition()
RETURNS TRIGGER AS $$
BEGIN
    NEW.date_partition = DATE(NEW.timestamp);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
CREATE TRIGGER set_api_usage_stats_date_partition
    BEFORE INSERT ON api_usage_stats
    FOR EACH ROW EXECUTE FUNCTION set_date_partition();

CREATE TRIGGER set_ai_model_usage_stats_date_partition
    BEFORE INSERT ON ai_model_usage_stats
    FOR EACH ROW EXECUTE FUNCTION set_date_partition();

-- ===========================================
-- 7. 数据维护函数
-- ===========================================

-- 清理过期审计日志的函数
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_months INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    -- 计算截止日期（保留指定月数）
    cutoff_date := CURRENT_TIMESTAMP - INTERVAL '1 month' * retention_months;
    
    -- 删除过期的审计日志
    DELETE FROM audit_logs 
    WHERE timestamp < cutoff_date;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '清理了 % 条过期的审计日志记录', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 清理过期使用统计的函数
CREATE OR REPLACE FUNCTION cleanup_old_usage_stats(retention_months INTEGER DEFAULT 12)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    temp_count INTEGER := 0;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    -- 计算截止日期（保留指定月数）
    cutoff_date := CURRENT_TIMESTAMP - INTERVAL '1 month' * retention_months;
    
    -- 删除过期的API使用统计
    DELETE FROM api_usage_stats 
    WHERE timestamp < cutoff_date;
    
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- 删除过期的AI模型使用统计
    DELETE FROM ai_model_usage_stats 
    WHERE timestamp < cutoff_date;
    
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    RAISE NOTICE '清理了 % 条过期的使用统计记录', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 刷新物化视图的函数
CREATE OR REPLACE FUNCTION refresh_usage_summaries()
RETURNS VOID AS $$
BEGIN
    -- 刷新日使用统计
    REFRESH MATERIALIZED VIEW daily_usage_summary;
    
    -- 刷新月使用统计
    REFRESH MATERIALIZED VIEW monthly_usage_summary;
    
    RAISE NOTICE '使用统计汇总视图已刷新';
END;
$$ LANGUAGE plpgsql;

-- 创建分区表的函数
CREATE OR REPLACE FUNCTION create_monthly_partitions(target_date DATE)
RETURNS VOID AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- 计算分区的开始和结束日期
    start_date := DATE_TRUNC('month', target_date);
    end_date := start_date + INTERVAL '1 month';
    
    -- 生成分区名称
    partition_name := 'audit_logs_' || TO_CHAR(start_date, 'YYYY_MM');
    
    -- 创建审计日志分区
    EXECUTE FORMAT(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_logs FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
    
    -- 创建API使用统计分区
    partition_name := 'api_usage_stats_' || TO_CHAR(start_date, 'YYYY_MM');
    EXECUTE FORMAT(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF api_usage_stats FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
    
    -- 创建AI模型使用统计分区
    partition_name := 'ai_model_usage_stats_' || TO_CHAR(start_date, 'YYYY_MM');
    EXECUTE FORMAT(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF ai_model_usage_stats FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
    
    RAISE NOTICE '为日期 % 创建了月份分区', start_date;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- 8. 租户隔离策略
-- ===========================================

-- 启用行级安全
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_model_usage_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE database_performance_metrics ENABLE ROW LEVEL SECURITY;

-- 创建租户隔离策略
CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    FOR ALL TO PUBLIC
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_api_usage_stats ON api_usage_stats
    FOR ALL TO PUBLIC
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_ai_model_usage_stats ON ai_model_usage_stats
    FOR ALL TO PUBLIC
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_system_performance_metrics ON system_performance_metrics
    FOR ALL TO PUBLIC
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation_database_performance_metrics ON database_performance_metrics
    FOR ALL TO PUBLIC
    USING (tenant_id = get_current_tenant_id());

-- 输出成功消息
DO $$
BEGIN
    RAISE NOTICE 'Lyss AI Platform - 共享数据库表结构创建成功';
END
$$;