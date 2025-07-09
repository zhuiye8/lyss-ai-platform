-- Lyss AI Platform - 种子数据
-- 此脚本插入系统初始化所需的种子数据

-- ===========================================
-- 1. 系统配置数据
-- ===========================================

-- 插入系统全局配置
INSERT INTO system_configs (config_key, config_value, description) VALUES
    ('system.version', '"1.0.0"', 'Lyss AI Platform 系统版本'),
    ('system.environment', '"development"', '系统环境（development/staging/production）'),
    ('system.maintenance_mode', 'false', '系统维护模式开关'),
    ('system.max_tenants', '1000', '系统支持的最大租户数量'),
    ('system.default_language', '"zh-CN"', '系统默认语言'),
    ('system.default_timezone', '"Asia/Shanghai"', '系统默认时区'),
    
    -- 安全配置
    ('security.jwt_expiry_hours', '24', 'JWT令牌过期时间（小时）'),
    ('security.password_min_length', '8', '密码最小长度'),
    ('security.max_login_attempts', '5', '最大登录尝试次数'),
    ('security.lockout_duration_minutes', '30', '账号锁定时间（分钟）'),
    ('security.session_timeout_minutes', '480', '会话超时时间（分钟）'),
    
    -- 速率限制配置
    ('rate_limit.api_requests_per_minute', '1000', 'API每分钟请求限制'),
    ('rate_limit.ai_requests_per_minute', '60', 'AI服务每分钟请求限制'),
    ('rate_limit.auth_requests_per_minute', '30', '认证每分钟请求限制'),
    
    -- 文件上传配置
    ('upload.max_file_size_mb', '10', '最大文件上传大小（MB）'),
    ('upload.allowed_file_types', '["jpg", "jpeg", "png", "gif", "pdf", "txt", "md", "doc", "docx"]', '允许的文件类型'),
    
    -- 邮件配置
    ('email.smtp_enabled', 'false', '是否启用SMTP邮件发送'),
    ('email.from_name', '"Lyss AI Platform"', '发件人名称'),
    ('email.from_email', '"noreply@lyss.ai"', '发件人邮箱'),
    
    -- 缓存配置
    ('cache.redis_enabled', 'true', '是否启用Redis缓存'),
    ('cache.default_ttl_seconds', '3600', '默认缓存TTL（秒）'),
    ('cache.max_memory_mb', '512', '最大缓存内存（MB）')
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = CURRENT_TIMESTAMP;

-- ===========================================
-- 2. AI供应商模板配置
-- ===========================================

-- 插入AI供应商模板
INSERT INTO ai_provider_templates (provider_name, provider_type, base_url, auth_method, required_fields, optional_fields, rate_limits, pricing_info) VALUES
    -- OpenAI
    ('OpenAI', 'openai', 'https://api.openai.com/v1', 'api_key', 
     '{"api_key": {"type": "string", "description": "OpenAI API密钥"}}',
     '{"organization": {"type": "string", "description": "组织ID"}}',
     '{"requests_per_minute": 3000, "tokens_per_minute": 90000}',
     '{"gpt-4": {"input": 0.00003, "output": 0.00006}, "gpt-3.5-turbo": {"input": 0.0000005, "output": 0.0000015}}'
    ),
    
    -- Anthropic
    ('Anthropic', 'anthropic', 'https://api.anthropic.com', 'api_key',
     '{"api_key": {"type": "string", "description": "Anthropic API密钥"}}',
     '{"version": {"type": "string", "description": "API版本", "default": "2023-06-01"}}',
     '{"requests_per_minute": 1000, "tokens_per_minute": 40000}',
     '{"claude-3-opus": {"input": 0.000015, "output": 0.000075}, "claude-3-sonnet": {"input": 0.000003, "output": 0.000015}}'
    ),
    
    -- Google
    ('Google', 'google', 'https://generativelanguage.googleapis.com/v1beta', 'api_key',
     '{"api_key": {"type": "string", "description": "Google API密钥"}}',
     '{"project_id": {"type": "string", "description": "项目ID"}}',
     '{"requests_per_minute": 1500, "tokens_per_minute": 32000}',
     '{"gemini-pro": {"input": 0.000001, "output": 0.000002}, "gemini-pro-vision": {"input": 0.000002, "output": 0.000004}}'
    ),
    
    -- Azure OpenAI
    ('Azure OpenAI', 'azure_openai', 'https://{resource}.openai.azure.com/openai/deployments/{deployment}', 'api_key',
     '{"api_key": {"type": "string", "description": "Azure OpenAI API密钥"}, "resource": {"type": "string", "description": "Azure资源名称"}, "deployment": {"type": "string", "description": "部署名称"}}',
     '{"api_version": {"type": "string", "description": "API版本", "default": "2023-12-01-preview"}}',
     '{"requests_per_minute": 2000, "tokens_per_minute": 60000}',
     '{"gpt-4": {"input": 0.00003, "output": 0.00006}, "gpt-35-turbo": {"input": 0.0000005, "output": 0.0000015}}'
    ),
    
    -- 阿里云百炼
    ('Alibaba Cloud', 'alibaba_cloud', 'https://dashscope.aliyuncs.com/api/v1', 'api_key',
     '{"api_key": {"type": "string", "description": "阿里云DashScope API密钥"}}',
     '{"region": {"type": "string", "description": "地区", "default": "cn-beijing"}}',
     '{"requests_per_minute": 500, "tokens_per_minute": 20000}',
     '{"qwen-turbo": {"input": 0.000002, "output": 0.000006}, "qwen-plus": {"input": 0.000004, "output": 0.000012}}'
    ),
    
    -- 讯飞星火
    ('iFlytek', 'iflytek', 'https://spark-api.xf-yun.com/v3.1', 'api_key',
     '{"app_id": {"type": "string", "description": "应用ID"}, "api_key": {"type": "string", "description": "API密钥"}, "api_secret": {"type": "string", "description": "API密钥"}}',
     '{"domain": {"type": "string", "description": "领域", "default": "generalv3"}}',
     '{"requests_per_minute": 200, "tokens_per_minute": 8000}',
     '{"spark-v3": {"input": 0.000003, "output": 0.000009}, "spark-v2": {"input": 0.000002, "output": 0.000006}}'
    ),
    
    -- 百度文心一言
    ('Baidu', 'baidu', 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop', 'api_key',
     '{"api_key": {"type": "string", "description": "百度API密钥"}, "secret_key": {"type": "string", "description": "百度密钥"}}',
     '{"model": {"type": "string", "description": "模型名称", "default": "ernie-bot"}}',
     '{"requests_per_minute": 300, "tokens_per_minute": 10000}',
     '{"ernie-bot": {"input": 0.000004, "output": 0.000008}, "ernie-bot-turbo": {"input": 0.000003, "output": 0.000006}}'
    )
ON CONFLICT (provider_name) DO UPDATE SET
    provider_type = EXCLUDED.provider_type,
    base_url = EXCLUDED.base_url,
    auth_method = EXCLUDED.auth_method,
    required_fields = EXCLUDED.required_fields,
    optional_fields = EXCLUDED.optional_fields,
    rate_limits = EXCLUDED.rate_limits,
    pricing_info = EXCLUDED.pricing_info,
    updated_at = CURRENT_TIMESTAMP;

-- ===========================================
-- 3. 默认租户数据
-- ===========================================

-- 插入系统管理员租户
INSERT INTO tenants (
    tenant_id,
    tenant_name,
    tenant_slug,
    contact_email,
    contact_name,
    company_name,
    status,
    subscription_plan,
    config
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Lyss Platform Admin',
    'lyss-admin',
    'admin@lyss.ai',
    'System Administrator',
    'Lyss AI Technologies',
    'active',
    'enterprise',
    '{
        "max_users": 1000,
        "max_conversations_per_user": 10000,
        "max_api_calls_per_month": 1000000,
        "max_storage_gb": 100.0,
        "max_memory_entries": 100000,
        "enabled_models": ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "gemini-pro"],
        "model_rate_limits": {
            "gpt-4": 1000,
            "gpt-3.5-turbo": 5000,
            "claude-3-sonnet": 1000,
            "gemini-pro": 2000
        },
        "features": {
            "conversation_memory": true,
            "file_upload": true,
            "api_access": true,
            "webhook_integration": true,
            "sso_integration": true,
            "audit_logs": true,
            "advanced_analytics": true,
            "custom_models": true
        },
        "branding": {
            "logo_url": "/assets/lyss-logo.png",
            "primary_color": "#1890ff",
            "secondary_color": "#52c41a",
            "company_name": "Lyss AI Technologies"
        },
        "security": {
            "enforce_2fa": false,
            "session_timeout_minutes": 480,
            "password_policy": {
                "min_length": 8,
                "require_uppercase": true,
                "require_lowercase": true,
                "require_numbers": true,
                "require_symbols": false
            }
        }
    }'::jsonb
) ON CONFLICT (tenant_id) DO UPDATE SET
    tenant_name = EXCLUDED.tenant_name,
    config = EXCLUDED.config,
    updated_at = CURRENT_TIMESTAMP;

-- 插入演示租户
INSERT INTO tenants (
    tenant_id,
    tenant_name,
    tenant_slug,
    contact_email,
    contact_name,
    company_name,
    status,
    subscription_plan,
    config
) VALUES (
    '00000000-0000-0000-0000-000000000002',
    'Demo Company',
    'demo-company',
    'demo@example.com',
    'Demo User',
    'Demo Company Inc.',
    'active',
    'professional',
    '{
        "max_users": 50,
        "max_conversations_per_user": 500,
        "max_api_calls_per_month": 50000,
        "max_storage_gb": 10.0,
        "max_memory_entries": 5000,
        "enabled_models": ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"],
        "model_rate_limits": {
            "gpt-4": 100,
            "gpt-3.5-turbo": 500,
            "claude-3-sonnet": 100
        },
        "features": {
            "conversation_memory": true,
            "file_upload": true,
            "api_access": true,
            "webhook_integration": false,
            "sso_integration": false,
            "audit_logs": true,
            "advanced_analytics": false,
            "custom_models": false
        },
        "branding": {
            "logo_url": "/assets/demo-logo.png",
            "primary_color": "#722ed1",
            "secondary_color": "#13c2c2",
            "company_name": "Demo Company Inc."
        },
        "security": {
            "enforce_2fa": false,
            "session_timeout_minutes": 240,
            "password_policy": {
                "min_length": 6,
                "require_uppercase": false,
                "require_lowercase": true,
                "require_numbers": false,
                "require_symbols": false
            }
        }
    }'::jsonb
) ON CONFLICT (tenant_id) DO UPDATE SET
    tenant_name = EXCLUDED.tenant_name,
    config = EXCLUDED.config,
    updated_at = CURRENT_TIMESTAMP;

-- 插入免费试用租户
INSERT INTO tenants (
    tenant_id,
    tenant_name,
    tenant_slug,
    contact_email,
    contact_name,
    company_name,
    status,
    subscription_plan,
    config
) VALUES (
    '00000000-0000-0000-0000-000000000003',
    'Free Trial User',
    'free-trial',
    'trial@example.com',
    'Trial User',
    'Personal',
    'trial',
    'free',
    '{
        "max_users": 1,
        "max_conversations_per_user": 10,
        "max_api_calls_per_month": 1000,
        "max_storage_gb": 1.0,
        "max_memory_entries": 100,
        "enabled_models": ["gpt-3.5-turbo"],
        "model_rate_limits": {
            "gpt-3.5-turbo": 20
        },
        "features": {
            "conversation_memory": true,
            "file_upload": false,
            "api_access": false,
            "webhook_integration": false,
            "sso_integration": false,
            "audit_logs": false,
            "advanced_analytics": false,
            "custom_models": false
        },
        "branding": {
            "logo_url": "/assets/default-logo.png",
            "primary_color": "#1890ff",
            "secondary_color": "#52c41a",
            "company_name": "Lyss AI Platform"
        },
        "security": {
            "enforce_2fa": false,
            "session_timeout_minutes": 120,
            "password_policy": {
                "min_length": 6,
                "require_uppercase": false,
                "require_lowercase": true,
                "require_numbers": false,
                "require_symbols": false
            }
        }
    }'::jsonb
) ON CONFLICT (tenant_id) DO UPDATE SET
    tenant_name = EXCLUDED.tenant_name,
    config = EXCLUDED.config,
    updated_at = CURRENT_TIMESTAMP;

-- ===========================================
-- 4. 租户配置数据
-- ===========================================

-- 为管理员租户添加额外配置
INSERT INTO tenant_configs (tenant_id, config_key, config_value, description) VALUES
    ('00000000-0000-0000-0000-000000000001', 'webhook.enabled', 'true', '是否启用Webhook'),
    ('00000000-0000-0000-0000-000000000001', 'webhook.url', '"https://admin.lyss.ai/webhooks"', 'Webhook URL'),
    ('00000000-0000-0000-0000-000000000001', 'sso.enabled', 'true', '是否启用SSO'),
    ('00000000-0000-0000-0000-000000000001', 'sso.provider', '"azure_ad"', 'SSO提供商'),
    ('00000000-0000-0000-0000-000000000001', 'custom_domain.enabled', 'true', '是否启用自定义域名'),
    ('00000000-0000-0000-0000-000000000001', 'custom_domain.domain', '"ai.lyss.ai"', '自定义域名'),
    ('00000000-0000-0000-0000-000000000001', 'analytics.enabled', 'true', '是否启用高级分析'),
    ('00000000-0000-0000-0000-000000000001', 'backup.enabled', 'true', '是否启用数据备份'),
    ('00000000-0000-0000-0000-000000000001', 'backup.frequency', '"daily"', '备份频率')
ON CONFLICT (tenant_id, config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = CURRENT_TIMESTAMP;

-- 为演示租户添加配置
INSERT INTO tenant_configs (tenant_id, config_key, config_value, description) VALUES
    ('00000000-0000-0000-0000-000000000002', 'demo.enabled', 'true', '是否为演示环境'),
    ('00000000-0000-0000-0000-000000000002', 'demo.auto_reset', 'true', '是否自动重置演示数据'),
    ('00000000-0000-0000-0000-000000000002', 'demo.reset_interval_hours', '24', '演示数据重置间隔（小时）'),
    ('00000000-0000-0000-0000-000000000002', 'backup.enabled', 'false', '是否启用数据备份')
ON CONFLICT (tenant_id, config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = CURRENT_TIMESTAMP;

-- 为试用租户添加配置
INSERT INTO tenant_configs (tenant_id, config_key, config_value, description) VALUES
    ('00000000-0000-0000-0000-000000000003', 'trial.enabled', 'true', '是否为试用环境'),
    ('00000000-0000-0000-0000-000000000003', 'trial.expires_at', to_jsonb((CURRENT_TIMESTAMP + INTERVAL '30 days')::text), '试用过期时间'),
    ('00000000-0000-0000-0000-000000000003', 'trial.warning_days', '7', '试用过期提醒天数'),
    ('00000000-0000-0000-0000-000000000003', 'backup.enabled', 'false', '是否启用数据备份')
ON CONFLICT (tenant_id, config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    updated_at = CURRENT_TIMESTAMP;

-- 输出成功消息
DO $$
BEGIN
    RAISE NOTICE 'Lyss AI Platform - 种子数据插入成功';
    RAISE NOTICE '已创建 % 个租户', (SELECT COUNT(*) FROM tenants);
    RAISE NOTICE '已创建 % 个系统配置', (SELECT COUNT(*) FROM system_configs);
    RAISE NOTICE '已创建 % 个AI供应商模板', (SELECT COUNT(*) FROM ai_provider_templates);
    RAISE NOTICE '已创建 % 个租户配置', (SELECT COUNT(*) FROM tenant_configs);
END
$$;