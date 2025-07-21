-- =====================================================
-- Lyss Provider Service 测试数据种子脚本
-- 创建开发和测试环境所需的基础数据
-- 
-- 作者: Lyss AI Team
-- 创建时间: 2025-01-21
-- 修改时间: 2025-01-21
-- =====================================================

-- 切换到供应商服务数据库
\c lyss_provider_db;

-- 开始事务
BEGIN;

-- =====================================================
-- 1. 清理现有测试数据（可选）
-- =====================================================
-- 注意：生产环境请勿执行此段
-- DELETE FROM proxy_request_logs WHERE tenant_id IN (SELECT id FROM test_tenants);
-- DELETE FROM channel_metrics WHERE channel_id IN (SELECT id FROM provider_channels WHERE tenant_id IN (SELECT id FROM test_tenants));
-- DELETE FROM tenant_quotas WHERE tenant_id IN (SELECT id FROM test_tenants);
-- DELETE FROM provider_channels WHERE tenant_id IN (SELECT id FROM test_tenants);

-- =====================================================
-- 2. 创建测试租户数据表（临时）
-- =====================================================
-- 创建临时表存储测试租户信息
CREATE TEMP TABLE test_tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(100),
    slug VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 插入测试租户数据
INSERT INTO test_tenants (id, name, slug) VALUES
('11111111-1111-1111-1111-111111111111', 'Lyss开发团队', 'dev-team'),
('22222222-2222-2222-2222-222222222222', 'Demo演示租户', 'demo-tenant'),
('33333333-3333-3333-3333-333333333333', 'AI研究实验室', 'ai-lab');

-- =====================================================
-- 3. 创建测试租户配额
-- =====================================================
INSERT INTO tenant_quotas (
    tenant_id, 
    daily_request_limit, 
    daily_token_limit,
    monthly_request_limit,
    monthly_token_limit,
    status
) VALUES 
-- 开发团队 - 高配额
('11111111-1111-1111-1111-111111111111', 50000, 5000000, 1500000, 150000000, 'active'),
-- Demo演示 - 中等配额
('22222222-2222-2222-2222-222222222222', 10000, 1000000, 300000, 30000000, 'active'),
-- AI实验室 - 研究用高配额
('33333333-3333-3333-3333-333333333333', 100000, 10000000, 3000000, 300000000, 'active');

-- =====================================================
-- 4. 创建测试Channel配置
-- =====================================================
-- 开发团队的Channel
INSERT INTO provider_channels (
    tenant_id,
    name,
    provider_id,
    base_url,
    credentials, -- 实际环境中这些应该是加密的
    models,
    status,
    priority,
    weight,
    max_requests_per_minute,
    config
) VALUES 
-- OpenAI Channels
('11111111-1111-1111-1111-111111111111', 'OpenAI主频道', 'openai', 'https://api.openai.com/v1',
 'encrypted_api_key_placeholder_openai_1', -- 这里应该是加密的API密钥
 '["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"]',
 'active', 1, 100, 1000,
 '{"timeout": 30, "max_retries": 3, "description": "主要OpenAI API频道"}'),

('11111111-1111-1111-1111-111111111111', 'OpenAI备用频道', 'openai', 'https://api.openai.com/v1',
 'encrypted_api_key_placeholder_openai_2',
 '["gpt-3.5-turbo", "gpt-4o-mini"]',
 'active', 2, 80, 800,
 '{"timeout": 30, "max_retries": 2, "description": "备用OpenAI API频道"}'),

-- Anthropic Channels
('11111111-1111-1111-1111-111111111111', 'Claude主频道', 'anthropic', 'https://api.anthropic.com',
 'encrypted_api_key_placeholder_anthropic_1',
 '["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-5-sonnet-20241022"]',
 'active', 1, 100, 600,
 '{"timeout": 30, "max_retries": 3, "description": "主要Anthropic API频道"}'),

-- Google Channels  
('11111111-1111-1111-1111-111111111111', 'Gemini频道', 'google', 'https://generativelanguage.googleapis.com/v1beta',
 'encrypted_api_key_placeholder_google_1',
 '["gemini-pro", "gemini-pro-vision"]',
 'active', 3, 60, 400,
 '{"timeout": 30, "max_retries": 2, "description": "Google Gemini API频道"}'),

-- Demo租户的Channel
('22222222-2222-2222-2222-222222222222', 'Demo-OpenAI', 'openai', 'https://api.openai.com/v1',
 'encrypted_api_key_placeholder_demo_openai',
 '["gpt-3.5-turbo", "gpt-4o-mini"]',
 'active', 1, 100, 200,
 '{"timeout": 30, "description": "Demo环境OpenAI频道"}'),

('22222222-2222-2222-2222-222222222222', 'Demo-Claude', 'anthropic', 'https://api.anthropic.com',
 'encrypted_api_key_placeholder_demo_anthropic',
 '["claude-3-haiku-20240307"]',
 'active', 2, 80, 150,
 '{"timeout": 30, "description": "Demo环境Claude频道"}'),

-- AI实验室的Channel
('33333333-3333-3333-3333-333333333333', 'Lab-GPT4', 'openai', 'https://api.openai.com/v1',
 'encrypted_api_key_placeholder_lab_openai',
 '["gpt-4", "gpt-4-turbo", "gpt-4o"]',
 'active', 1, 100, 2000,
 '{"timeout": 60, "max_retries": 5, "description": "实验室GPT-4频道"}'),

('33333333-3333-3333-3333-333333333333', 'Lab-Claude3', 'anthropic', 'https://api.anthropic.com',
 'encrypted_api_key_placeholder_lab_anthropic',
 '["claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]',
 'active', 1, 100, 1000,
 '{"timeout": 60, "max_retries": 5, "description": "实验室Claude-3频道"}'),

('33333333-3333-3333-3333-333333333333', 'Lab-DeepSeek', 'deepseek', 'https://api.deepseek.com',
 'encrypted_api_key_placeholder_lab_deepseek',
 '["deepseek-chat", "deepseek-coder"]',
 'active', 2, 70, 800,
 '{"timeout": 45, "max_retries": 3, "description": "实验室DeepSeek频道"}');

-- =====================================================
-- 5. 初始化Channel指标数据
-- =====================================================
-- 为所有创建的Channel初始化指标记录
INSERT INTO channel_metrics (
    channel_id,
    total_requests,
    successful_requests,
    failed_requests,
    total_tokens,
    avg_response_time,
    success_rate,
    health_status,
    health_check_time
)
SELECT 
    id,
    CASE 
        WHEN name LIKE '%主频道%' OR name LIKE '%Lab-GPT4%' THEN 1500 + FLOOR(RANDOM() * 500)
        WHEN name LIKE '%备用%' OR name LIKE '%Demo%' THEN 300 + FLOOR(RANDOM() * 200)
        ELSE 800 + FLOOR(RANDOM() * 400)
    END,
    CASE 
        WHEN name LIKE '%主频道%' OR name LIKE '%Lab-GPT4%' THEN 1400 + FLOOR(RANDOM() * 450)
        WHEN name LIKE '%备用%' OR name LIKE '%Demo%' THEN 280 + FLOOR(RANDOM() * 180)
        ELSE 750 + FLOOR(RANDOM() * 350)
    END,
    CASE 
        WHEN name LIKE '%主频道%' OR name LIKE '%Lab-GPT4%' THEN 5 + FLOOR(RANDOM() * 15)
        WHEN name LIKE '%备用%' OR name LIKE '%Demo%' THEN 2 + FLOOR(RANDOM() * 8)
        ELSE 8 + FLOOR(RANDOM() * 12)
    END,
    CASE 
        WHEN provider_id = 'openai' THEN 50000 + FLOOR(RANDOM() * 30000)
        WHEN provider_id = 'anthropic' THEN 40000 + FLOOR(RANDOM() * 25000)
        WHEN provider_id = 'google' THEN 30000 + FLOOR(RANDOM() * 20000)
        ELSE 35000 + FLOOR(RANDOM() * 15000)
    END,
    800 + RANDOM() * 1200, -- 800-2000ms响应时间
    CASE 
        WHEN name LIKE '%主频道%' OR name LIKE '%Lab-%' THEN 0.95 + RANDOM() * 0.04
        WHEN name LIKE '%备用%' THEN 0.90 + RANDOM() * 0.08
        ELSE 0.92 + RANDOM() * 0.06
    END,
    CASE 
        WHEN RANDOM() > 0.1 THEN 'healthy'
        ELSE 'checking'
    END,
    NOW() - INTERVAL '1 minute' * FLOOR(RANDOM() * 60)
FROM provider_channels;

-- 更新一些Channel的最后使用时间
UPDATE channel_metrics 
SET 
    last_request_time = NOW() - INTERVAL '1 minute' * FLOOR(RANDOM() * 30),
    last_success_time = NOW() - INTERVAL '1 minute' * FLOOR(RANDOM() * 45),
    requests_per_minute = CASE 
        WHEN total_requests > 1000 THEN 15 + RANDOM() * 25
        WHEN total_requests > 500 THEN 8 + RANDOM() * 15
        ELSE 3 + RANDOM() * 8
    END;

-- =====================================================
-- 6. 创建模拟请求日志数据（近7天）
-- =====================================================
-- 创建临时表存储要生成的日志数据
CREATE TEMP TABLE temp_log_data AS
SELECT 
    c.tenant_id,
    c.id as channel_id,
    c.provider_id,
    CASE c.provider_id
        WHEN 'openai' THEN 
            (ARRAY['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini'])[FLOOR(1 + RANDOM() * 5)]
        WHEN 'anthropic' THEN 
            (ARRAY['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-5-sonnet-20241022'])[FLOOR(1 + RANDOM() * 3)]
        WHEN 'google' THEN 
            (ARRAY['gemini-pro', 'gemini-pro-vision'])[FLOOR(1 + RANDOM() * 2)]
        ELSE 'deepseek-chat'
    END as model,
    '/v1/chat/completions' as endpoint,
    CASE 
        WHEN RANDOM() > 0.05 THEN 200 -- 95% 成功
        WHEN RANDOM() > 0.5 THEN 429   -- 限流错误
        WHEN RANDOM() > 0.7 THEN 500   -- 服务器错误
        ELSE 400                       -- 客户端错误
    END as status_code,
    500 + RANDOM() * 3000 as response_time, -- 500-3500ms
    50 + FLOOR(RANDOM() * 200) as prompt_tokens,    -- 50-250 tokens
    20 + FLOOR(RANDOM() * 500) as completion_tokens, -- 20-520 tokens
    CASE WHEN RANDOM() > 0.8 THEN TRUE ELSE FALSE END as is_stream,
    NOW() - INTERVAL '1 day' * RANDOM() * 7 as created_at -- 过去7天内随机时间
FROM provider_channels c,
     generate_series(1, 100) -- 每个Channel生成100条日志
WHERE c.status = 'active';

-- 插入日志数据，并计算total_tokens
INSERT INTO proxy_request_logs (
    tenant_id,
    channel_id,
    provider_id,
    model,
    request_id,
    method,
    endpoint,
    status_code,
    response_time,
    prompt_tokens,
    completion_tokens,
    total_tokens,
    is_stream,
    client_ip,
    user_agent,
    error_message,
    created_at
)
SELECT 
    tenant_id,
    channel_id,
    provider_id,
    model,
    'req_' || substr(md5(random()::text), 1, 16) as request_id,
    'POST' as method,
    endpoint,
    status_code,
    response_time,
    prompt_tokens,
    completion_tokens,
    prompt_tokens + completion_tokens as total_tokens,
    is_stream,
    ('192.168.1.' || FLOOR(1 + RANDOM() * 254))::INET as client_ip,
    CASE 
        WHEN RANDOM() > 0.7 THEN 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        WHEN RANDOM() > 0.4 THEN 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15'
        ELSE 'Python-httpx/0.24.1'
    END as user_agent,
    CASE 
        WHEN status_code >= 400 THEN 
            CASE status_code
                WHEN 400 THEN 'Invalid request format'
                WHEN 429 THEN 'Rate limit exceeded'
                WHEN 500 THEN 'Internal server error'
                ELSE 'Unknown error'
            END
        ELSE NULL
    END as error_message,
    created_at
FROM temp_log_data;

-- =====================================================
-- 7. 更新配额使用情况（基于生成的日志）
-- =====================================================
-- 更新每日配额使用
UPDATE tenant_quotas tq
SET 
    daily_requests_used = (
        SELECT COUNT(*)
        FROM proxy_request_logs rl
        WHERE rl.tenant_id = tq.tenant_id 
          AND DATE(rl.created_at) = CURRENT_DATE
    ),
    daily_tokens_used = (
        SELECT COALESCE(SUM(rl.total_tokens), 0)
        FROM proxy_request_logs rl
        WHERE rl.tenant_id = tq.tenant_id 
          AND DATE(rl.created_at) = CURRENT_DATE
    ),
    monthly_requests_used = (
        SELECT COUNT(*)
        FROM proxy_request_logs rl
        WHERE rl.tenant_id = tq.tenant_id 
          AND DATE_TRUNC('month', rl.created_at) = DATE_TRUNC('month', CURRENT_DATE)
    ),
    monthly_tokens_used = (
        SELECT COALESCE(SUM(rl.total_tokens), 0)
        FROM proxy_request_logs rl
        WHERE rl.tenant_id = tq.tenant_id 
          AND DATE_TRUNC('month', rl.created_at) = DATE_TRUNC('month', CURRENT_DATE)
    );

-- =====================================================
-- 8. 刷新Channel指标（基于实际日志数据）
-- =====================================================
-- 更新所有Channel的指标数据
DO $$
DECLARE
    channel_record RECORD;
BEGIN
    FOR channel_record IN SELECT id FROM provider_channels LOOP
        PERFORM update_channel_metrics(channel_record.id);
    END LOOP;
END $$;

-- =====================================================
-- 9. 创建一些异常状态的数据（用于测试）
-- =====================================================
-- 创建一个不健康的Channel用于测试
INSERT INTO provider_channels (
    tenant_id,
    name,
    provider_id,
    base_url,
    credentials,
    models,
    status,
    priority,
    weight,
    max_requests_per_minute,
    config
) VALUES 
('11111111-1111-1111-1111-111111111111', 'Test-Unhealthy-Channel', 'openai', 'https://api.openai.com/v1',
 'encrypted_invalid_api_key',
 '["gpt-3.5-turbo"]',
 'active', 10, 10, 100,
 '{"timeout": 30, "description": "测试用不健康频道"}');

-- 为不健康Channel创建指标数据
INSERT INTO channel_metrics (
    channel_id,
    total_requests,
    successful_requests,
    failed_requests,
    total_tokens,
    avg_response_time,
    success_rate,
    health_status,
    consecutive_failures,
    last_error_time
)
SELECT 
    id,
    50,   -- 总请求数
    10,   -- 成功请求数
    40,   -- 失败请求数
    5000, -- 总tokens
    5000, -- 高响应时间
    0.2,  -- 低成功率
    'unhealthy',
    5,    -- 连续失败次数
    NOW() - INTERVAL '5 minutes'
FROM provider_channels 
WHERE name = 'Test-Unhealthy-Channel';

-- 提交事务
COMMIT;

-- =====================================================
-- 10. 验证数据和输出统计
-- =====================================================
-- 显示创建的测试数据统计
SELECT 
    '=== 测试数据创建完成 ===' as status;

SELECT 
    'Tenant配额' as 数据类型,
    COUNT(*) as 数量,
    SUM(daily_request_limit) as 每日请求限制总和,
    SUM(daily_requests_used) as 每日已使用总和
FROM tenant_quotas;

SELECT 
    'Provider配置' as 数据类型,
    COUNT(*) as 数量,
    STRING_AGG(provider_id, ', ') as 供应商列表
FROM provider_configs;

SELECT 
    'Channel配置' as 数据类型,
    COUNT(*) as 总数量,
    COUNT(*) FILTER (WHERE status = 'active') as 活跃数量,
    COUNT(DISTINCT provider_id) as 供应商数量,
    COUNT(DISTINCT tenant_id) as 租户数量
FROM provider_channels;

SELECT 
    'Channel指标' as 数据类型,
    COUNT(*) as 数量,
    COUNT(*) FILTER (WHERE health_status = 'healthy') as 健康数量,
    COUNT(*) FILTER (WHERE health_status = 'unhealthy') as 不健康数量,
    ROUND(AVG(success_rate), 3) as 平均成功率
FROM channel_metrics;

SELECT 
    'API请求日志' as 数据类型,
    COUNT(*) as 总日志数,
    COUNT(*) FILTER (WHERE status_code = 200) as 成功请求数,
    COUNT(*) FILTER (WHERE status_code >= 400) as 失败请求数,
    ROUND(AVG(response_time), 2) as 平均响应时间ms,
    SUM(total_tokens) as 总Token使用量
FROM proxy_request_logs;

SELECT 
    'Channel使用情况' as 数据类型,
    c.name as Channel名称,
    c.provider_id as 供应商,
    m.total_requests as 总请求数,
    ROUND(m.success_rate, 3) as 成功率,
    m.health_status as 健康状态
FROM provider_channels c
LEFT JOIN channel_metrics m ON c.id = m.channel_id
ORDER BY m.total_requests DESC NULLS LAST;

-- 输出完成信息
SELECT 
    '🎉 Provider Service 测试数据初始化完成！' as message,
    '数据包含：3个测试租户、10个Channel、' || (SELECT COUNT(*) FROM proxy_request_logs) || '条模拟日志' as details;