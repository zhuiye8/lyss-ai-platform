-- ================================================================
-- Lyss AI Platform - 基础表结构
-- 
-- 包含：系统角色、租户、基础用户等核心表
-- 执行顺序：第1步
-- ================================================================

-- =============================================
-- 1. 系统角色定义表
-- =============================================
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
-- 2. 租户表
-- =============================================
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

-- =============================================
-- 3. 基础用户表
-- =============================================
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
-- 4. 审计日志表
-- =============================================
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
-- 5. 插入系统默认角色
-- =============================================
INSERT INTO roles (name, display_name, description, is_system_role, permissions) 
VALUES 
    ('super_admin', '超级管理员', '拥有系统最高权限，可管理所有租户', true, 
     '["tenant:create", "tenant:delete", "system:config", "user:manage_all"]'::jsonb),
    ('tenant_admin', '租户管理员', '租户级管理员，可管理租户内所有资源', true,
     '["user:create", "user:manage", "provider:manage", "tool:config", "memory:manage"]'::jsonb),
    ('end_user', '终端用户', '普通用户，可使用AI对话功能', true,
     '["chat:access", "memory:view", "preference:manage"]'::jsonb)
ON CONFLICT (name) DO NOTHING;

-- =============================================
-- 6. 插入默认测试租户和用户
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

-- 插入默认测试管理员用户 (密码: admin123)
INSERT INTO users (
    id, tenant_id, email, username, hashed_password, 
    first_name, last_name, role_id, is_active, email_verified
)
SELECT 
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'admin@lyss.dev',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBF7Pn0A8ZSc0m',
    'System',
    'Administrator',
    r.id,
    true,
    true
FROM roles r
WHERE r.name = 'tenant_admin'
ON CONFLICT (tenant_id, email) DO NOTHING;

-- 插入默认测试普通用户 (密码: user123)
INSERT INTO users (
    id, tenant_id, email, username, hashed_password,
    first_name, last_name, role_id, is_active, email_verified
)
SELECT 
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000001', 
    'user@lyss.dev',
    'testuser',
    '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
    'Test',
    'User',
    r.id,
    true,
    true
FROM roles r  
WHERE r.name = 'end_user'
ON CONFLICT (tenant_id, email) DO NOTHING;

-- =============================================
-- 7. 创建更新时间触发器函数
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表添加更新时间触发器
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 8. 添加表注释
-- =============================================
COMMENT ON TABLE roles IS '系统角色定义表，存储所有可用的用户角色';
COMMENT ON TABLE tenants IS '租户表 - 存储多租户系统的租户信息';
COMMENT ON TABLE users IS '基础用户表 - 存储多租户隔离的用户信息';
COMMENT ON TABLE audit_logs IS '审计日志表 - 记录所有关键操作用于安全审计';

-- 输出初始化完成信息
SELECT 
    '✅ 基础表结构初始化完成' as status,
    COUNT(*) as total_base_tables
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('roles', 'tenants', 'users', 'audit_logs');