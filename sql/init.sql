-- Lyss AI Platform 数据库初始化脚本
-- 创建基础数据库、扩展和初始数据

-- =============================================
-- 1. 创建必要的扩展
-- =============================================

-- 启用 pgcrypto 扩展用于加密存储
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 启用 uuid-ossp 扩展用于 UUID 生成
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用 btree_gin 扩展用于 JSONB 索引优化
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- =============================================
-- 2. 创建基础角色表 (全局共享)
-- =============================================

-- 系统角色定义表
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]'::jsonb,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建角色索引
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_system ON roles(is_system_role);

-- =============================================
-- 3. 插入系统默认角色
-- =============================================

-- 插入系统角色（如果不存在）
INSERT INTO roles (name, display_name, description, is_system_role, permissions) 
VALUES 
    ('super_admin', '超级管理员', '拥有系统最高权限，可管理所有租户', true, 
     '["tenant:create", "tenant:delete", "system:config", "user:manage_all"]'::jsonb),
    ('tenant_admin', '租户管理员', '租户级管理员，可管理租户内所有资源', true,
     '["user:create", "user:manage", "supplier:manage", "tool:config", "memory:manage"]'::jsonb),
    ('end_user', '终端用户', '普通用户，可使用AI对话功能', true,
     '["chat:access", "memory:view", "preference:manage"]'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- =============================================
-- 4. 创建租户相关表
-- =============================================

-- 租户表
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'inactive')),
    subscription_plan VARCHAR(50) DEFAULT 'basic',
    max_users INTEGER DEFAULT 10,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 租户索引
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

-- 用户表 (多租户隔离)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 多租户唯一约束
    CONSTRAINT uk_users_tenant_email UNIQUE(tenant_id, email),
    CONSTRAINT uk_users_tenant_username UNIQUE(tenant_id, username)
);

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- =============================================
-- 5. 创建供应商凭证表 (加密存储)
-- =============================================

-- 供应商凭证表
CREATE TABLE IF NOT EXISTS supplier_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider_name VARCHAR(50) NOT NULL, 
    display_name VARCHAR(100) NOT NULL,
    encrypted_api_key BYTEA NOT NULL, -- 使用 pgcrypto 加密
    base_url VARCHAR(255),
    model_configs JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 租户内供应商配置唯一
    CONSTRAINT uk_supplier_tenant_provider_display UNIQUE(tenant_id, provider_name, display_name)
);

-- 供应商凭证索引
CREATE INDEX IF NOT EXISTS idx_supplier_credentials_tenant_id ON supplier_credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_supplier_credentials_provider ON supplier_credentials(provider_name);
CREATE INDEX IF NOT EXISTS idx_supplier_credentials_active ON supplier_credentials(is_active);

-- =============================================
-- 6. 创建工具配置表
-- =============================================

-- 租户工具配置表
CREATE TABLE IF NOT EXISTS tenant_tool_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_name VARCHAR(100) NOT NULL,
    tool_node_name VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    config_params JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 租户内工具配置唯一
    CONSTRAINT uk_tool_config_tenant_workflow_tool UNIQUE(tenant_id, workflow_name, tool_node_name)
);

-- 工具配置索引
CREATE INDEX IF NOT EXISTS idx_tool_configs_tenant_id ON tenant_tool_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tool_configs_workflow ON tenant_tool_configs(workflow_name);

-- =============================================
-- 7. 创建用户偏好表
-- =============================================

-- 用户偏好设置表
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    active_memory_enabled BOOLEAN DEFAULT TRUE,
    preferred_language VARCHAR(10) DEFAULT 'zh',
    theme VARCHAR(20) DEFAULT 'light',
    notification_settings JSONB DEFAULT '{}'::jsonb,
    ai_model_preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 用户偏好唯一
    CONSTRAINT uk_user_preferences_user_tenant UNIQUE(user_id, tenant_id)
);

-- 用户偏好索引
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_tenant_id ON user_preferences(tenant_id);

-- =============================================
-- 8. 创建会话和对话表
-- =============================================

-- 用户会话表 (Auth Service 使用)
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    refresh_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    refresh_expires_at TIMESTAMP NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 会话表索引
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- 对话表 (对话历史存储)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255),
    workflow_type VARCHAR(50) DEFAULT 'simple_chat',
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 对话表索引
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message ON conversations(last_message_at);
CREATE INDEX IF NOT EXISTS idx_conversations_archived ON conversations(is_archived);

-- =============================================
-- 9. 创建审计日志表
-- =============================================

-- 系统审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    operation VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(255),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 审计日志索引
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_operation ON audit_logs(operation);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_request_id ON audit_logs(request_id);

-- =============================================
-- 10. 创建默认测试租户和用户 (开发环境)
-- =============================================

-- 插入默认测试租户
INSERT INTO tenants (id, name, slug, subscription_plan, max_users, settings)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Lyss 开发测试租户',
    'dev-tenant',
    'enterprise',
    100,
    '{"timezone": "Asia/Shanghai", "default_language": "zh"}'::jsonb
) ON CONFLICT (slug) DO NOTHING;

-- 插入默认测试管理员用户
-- 密码: admin123 (使用 bcrypt 加密)
INSERT INTO users (
    id, tenant_id, email, username, hashed_password, 
    first_name, last_name, role_id, is_active, email_verified
)
SELECT 
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'admin@lyss.dev',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBF7Pn0A8ZSc0m', -- admin123
    'System',
    'Administrator',
    r.id,
    true,
    true
FROM roles r
WHERE r.name = 'tenant_admin'
ON CONFLICT (tenant_id, email) DO NOTHING;

-- 插入默认测试普通用户
-- 密码: user123 (使用 bcrypt 加密)
INSERT INTO users (
    id, tenant_id, email, username, hashed_password,
    first_name, last_name, role_id, is_active, email_verified
)
SELECT 
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000001', 
    'user@lyss.dev',
    'testuser',
    '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', -- user123
    'Test',
    'User',
    r.id,
    true,
    true
FROM roles r  
WHERE r.name = 'end_user'
ON CONFLICT (tenant_id, email) DO NOTHING;

-- 为默认用户创建偏好设置
INSERT INTO user_preferences (user_id, tenant_id, active_memory_enabled, preferred_language, theme)
VALUES 
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', true, 'zh', 'light'),
    ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', true, 'zh', 'light')
ON CONFLICT (user_id, tenant_id) DO NOTHING;

-- =============================================
-- 11. 创建更新时间触发器函数
-- =============================================

-- 自动更新 updated_at 字段的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有需要的表添加更新时间触发器
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_supplier_credentials_updated_at BEFORE UPDATE ON supplier_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_tool_configs_updated_at BEFORE UPDATE ON tenant_tool_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_sessions_updated_at BEFORE UPDATE ON user_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 12. 数据库统计信息和注释
-- =============================================

-- 为重要表添加注释
COMMENT ON TABLE tenants IS '租户表 - 存储多租户系统的租户信息';
COMMENT ON TABLE users IS '用户表 - 存储多租户隔离的用户信息';
COMMENT ON TABLE supplier_credentials IS '供应商凭证表 - 加密存储AI供应商API密钥';
COMMENT ON TABLE tenant_tool_configs IS '工具配置表 - 存储租户级别的EINO工具开关配置';
COMMENT ON TABLE user_preferences IS '用户偏好表 - 存储用户个性化设置包括记忆开关';
COMMENT ON TABLE conversations IS '对话表 - 存储用户对话历史记录';
COMMENT ON TABLE audit_logs IS '审计日志表 - 记录所有关键操作用于安全审计';

-- 输出初始化完成信息
SELECT '✅ Lyss AI Platform 数据库初始化完成!' as message,
       COUNT(*) as total_tables
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';