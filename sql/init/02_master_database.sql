-- Lyss AI Platform - 主数据库表结构
-- 此脚本创建主数据库的表结构，用于租户管理和系统配置

-- ===========================================
-- 1. 租户管理表
-- ===========================================

-- 租户主表
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_name VARCHAR(255) NOT NULL UNIQUE,
    tenant_slug VARCHAR(100) NOT NULL UNIQUE, -- URL友好的租户标识
    
    -- 联系信息
    contact_email CITEXT NOT NULL,
    contact_name VARCHAR(255),
    company_name VARCHAR(255),
    
    -- 状态和订阅
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'suspended', 'deleted', 'trial')),
    subscription_plan VARCHAR(20) DEFAULT 'free' NOT NULL 
        CHECK (subscription_plan IN ('free', 'basic', 'professional', 'enterprise')),
    
    -- 数据库连接配置（加密存储）
    db_connection_config TEXT, -- 加密的数据库连接配置
    
    -- 租户配置（JSONB格式）
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- 元数据
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 租户配置表
CREATE TABLE IF NOT EXISTS tenant_configs (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, config_key)
);

-- ===========================================
-- 2. 系统配置表
-- ===========================================

-- 系统全局配置
CREATE TABLE IF NOT EXISTS system_configs (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI供应商模板配置
CREATE TABLE IF NOT EXISTS ai_provider_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- ===========================================
-- 3. 索引创建
-- ===========================================

-- 租户表索引
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(tenant_slug);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_plan ON tenants(subscription_plan);
CREATE INDEX IF NOT EXISTS idx_tenants_config ON tenants USING gin(config);
CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants(created_at);

-- 租户配置表索引
CREATE INDEX IF NOT EXISTS idx_tenant_configs_tenant_id ON tenant_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_configs_key ON tenant_configs(config_key);

-- 系统配置表索引
CREATE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(config_key);

-- AI供应商模板索引
CREATE INDEX IF NOT EXISTS idx_ai_provider_templates_type ON ai_provider_templates(provider_type);
CREATE INDEX IF NOT EXISTS idx_ai_provider_templates_active ON ai_provider_templates(is_active);

-- ===========================================
-- 4. 触发器函数
-- ===========================================

-- 更新updated_at时间戳的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 租户配置验证触发器函数
CREATE OR REPLACE FUNCTION validate_tenant_config()
RETURNS TRIGGER AS $$
BEGIN
    -- 验证最大用户数
    IF (NEW.config->>'max_users')::INTEGER <= 0 THEN
        RAISE EXCEPTION '最大用户数必须大于0';
    END IF;
    
    -- 验证每月API调用限制
    IF (NEW.config->>'max_api_calls_per_month')::INTEGER < 0 THEN
        RAISE EXCEPTION '每月API调用限制不能为负数';
    END IF;
    
    -- 根据订阅计划验证限制
    CASE NEW.subscription_plan
        WHEN 'free' THEN
            IF (NEW.config->>'max_users')::INTEGER > 5 THEN
                RAISE EXCEPTION '免费计划最多支持5个用户';
            END IF;
        WHEN 'basic' THEN
            IF (NEW.config->>'max_users')::INTEGER > 25 THEN
                RAISE EXCEPTION '基础计划最多支持25个用户';
            END IF;
        WHEN 'professional' THEN
            IF (NEW.config->>'max_users')::INTEGER > 100 THEN
                RAISE EXCEPTION '专业计划最多支持100个用户';
            END IF;
        ELSE
            -- 企业版无限制
            NULL;
    END CASE;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- 5. 创建触发器
-- ===========================================

-- 为所有表创建updated_at触发器
CREATE TRIGGER update_tenants_updated_at 
    BEFORE UPDATE ON tenants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_configs_updated_at 
    BEFORE UPDATE ON tenant_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_configs_updated_at 
    BEFORE UPDATE ON system_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_provider_templates_updated_at 
    BEFORE UPDATE ON ai_provider_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 租户配置验证触发器
CREATE TRIGGER validate_tenant_config_trigger
    BEFORE INSERT OR UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION validate_tenant_config();

-- ===========================================
-- 6. 数据库连接配置加密触发器
-- ===========================================

-- 数据库连接配置加密触发器函数
CREATE OR REPLACE FUNCTION encrypt_db_connection_config()
RETURNS TRIGGER AS $$
BEGIN
    -- 只在连接配置发生变化时加密
    IF NEW.db_connection_config IS NOT NULL AND 
       (OLD.db_connection_config IS NULL OR NEW.db_connection_config != OLD.db_connection_config) THEN
        NEW.db_connection_config = encrypt_data(NEW.db_connection_config, 'db_connection');
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建数据库连接配置加密触发器
CREATE TRIGGER encrypt_db_connection_config_trigger
    BEFORE INSERT OR UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION encrypt_db_connection_config();

-- 输出成功消息
DO $$
BEGIN
    RAISE NOTICE 'Lyss AI Platform - 主数据库表结构创建成功';
END
$$;