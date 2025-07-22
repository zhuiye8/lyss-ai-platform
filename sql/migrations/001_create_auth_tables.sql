-- =====================================================
-- Lyss Auth Service 数据库表结构
-- 认证服务相关的所有表结构
-- 
-- 作者: Lyss AI Team  
-- 创建时间: 2025-01-21
-- 修改时间: 2025-01-21
-- =====================================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =====================================================
-- 1. 系统角色定义表
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]',
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建角色索引
CREATE INDEX idx_auth_roles_name ON auth_roles(name);
CREATE INDEX idx_auth_roles_system ON auth_roles(is_system_role);

-- 添加注释
COMMENT ON TABLE auth_roles IS '系统角色定义表，存储所有可用的用户角色';
COMMENT ON COLUMN auth_roles.name IS '角色名称，系统内唯一标识';
COMMENT ON COLUMN auth_roles.display_name IS '角色显示名称';
COMMENT ON COLUMN auth_roles.permissions IS '角色拥有的权限列表，JSON数组格式';
COMMENT ON COLUMN auth_roles.is_system_role IS '是否为系统内置角色，不可删除';

-- =====================================================
-- 2. 用户表
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role_id UUID NOT NULL REFERENCES auth_roles(id) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255), -- TOTP密钥，加密存储
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP WITH TIME ZONE,
    email_verification_token VARCHAR(255),
    email_verification_expires TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 多租户唯一约束
    CONSTRAINT uk_auth_users_tenant_email UNIQUE(tenant_id, email),
    CONSTRAINT uk_auth_users_tenant_username UNIQUE(tenant_id, username),
    CONSTRAINT chk_login_attempts CHECK (login_attempts >= 0 AND login_attempts <= 10)
);

-- 创建用户表索引
CREATE INDEX idx_auth_users_tenant_id ON auth_users(tenant_id);
CREATE INDEX idx_auth_users_email ON auth_users(email);
CREATE INDEX idx_auth_users_role_id ON auth_users(role_id);
CREATE INDEX idx_auth_users_active ON auth_users(is_active);
CREATE INDEX idx_auth_users_locked ON auth_users(locked_until) WHERE locked_until IS NOT NULL;
CREATE INDEX idx_auth_users_password_reset ON auth_users(password_reset_token) WHERE password_reset_token IS NOT NULL;
CREATE INDEX idx_auth_users_email_verification ON auth_users(email_verification_token) WHERE email_verification_token IS NOT NULL;

-- 添加注释
COMMENT ON TABLE auth_users IS '用户表，存储所有用户的基本信息和认证数据';
COMMENT ON COLUMN auth_users.tenant_id IS '租户ID，用于多租户数据隔离';
COMMENT ON COLUMN auth_users.hashed_password IS 'bcrypt加密后的密码哈希';
COMMENT ON COLUMN auth_users.login_attempts IS '连续登录失败次数，超过限制将被锁定';
COMMENT ON COLUMN auth_users.locked_until IS '账户锁定截止时间';
COMMENT ON COLUMN auth_users.mfa_enabled IS '是否启用多因素认证';
COMMENT ON COLUMN auth_users.mfa_secret IS '多因素认证密钥，pgcrypto加密存储';

-- =====================================================
-- 3. 用户会话表
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    refresh_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    refresh_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_session_expires CHECK (expires_at > created_at),
    CONSTRAINT chk_refresh_expires CHECK (refresh_expires_at > expires_at)
);

-- 创建会话表索引
CREATE INDEX idx_auth_sessions_user_id ON auth_user_sessions(user_id);
CREATE INDEX idx_auth_sessions_session_token ON auth_user_sessions(session_token);
CREATE INDEX idx_auth_sessions_refresh_token ON auth_user_sessions(refresh_token);
CREATE INDEX idx_auth_sessions_active ON auth_user_sessions(is_active);
CREATE INDEX idx_auth_sessions_expires ON auth_user_sessions(expires_at);
CREATE INDEX idx_auth_sessions_tenant_user ON auth_user_sessions(tenant_id, user_id);

-- 添加注释
COMMENT ON TABLE auth_user_sessions IS '用户会话表，存储JWT令牌和会话信息';
COMMENT ON COLUMN auth_user_sessions.session_token IS 'JWT访问令牌ID';
COMMENT ON COLUMN auth_user_sessions.refresh_token IS 'JWT刷新令牌ID';
COMMENT ON COLUMN auth_user_sessions.device_info IS '设备信息JSON，包含浏览器、操作系统等';

-- =====================================================
-- 4. JWT令牌黑名单表
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_token_blacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_jti VARCHAR(255) NOT NULL UNIQUE, -- JWT ID
    token_type VARCHAR(20) NOT NULL CHECK (token_type IN ('access', 'refresh')),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    blacklisted_reason VARCHAR(100),
    blacklisted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建黑名单索引
CREATE INDEX idx_auth_blacklist_jti ON auth_token_blacklist(token_jti);
CREATE INDEX idx_auth_blacklist_user ON auth_token_blacklist(user_id);
CREATE INDEX idx_auth_blacklist_expires ON auth_token_blacklist(expires_at);
CREATE INDEX idx_auth_blacklist_type ON auth_token_blacklist(token_type);

-- 添加注释
COMMENT ON TABLE auth_token_blacklist IS 'JWT令牌黑名单表，用于令牌撤销和安全控制';
COMMENT ON COLUMN auth_token_blacklist.token_jti IS 'JWT的JTI声明，令牌唯一标识';
COMMENT ON COLUMN auth_token_blacklist.blacklisted_reason IS '加入黑名单的原因';

-- =====================================================
-- 5. OAuth2提供商配置表
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_oauth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider_name VARCHAR(50) NOT NULL, -- google, github, microsoft, azure
    display_name VARCHAR(100) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    encrypted_client_secret TEXT NOT NULL, -- pgcrypto加密存储
    auth_url VARCHAR(500) NOT NULL,
    token_url VARCHAR(500) NOT NULL,
    user_info_url VARCHAR(500) NOT NULL,
    redirect_uri VARCHAR(500) NOT NULL,
    scopes TEXT[] DEFAULT ARRAY['openid', 'profile', 'email'],
    additional_config JSONB DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uk_auth_oauth_tenant_provider UNIQUE(tenant_id, provider_name),
    CONSTRAINT chk_oauth_provider_name CHECK (
        provider_name IN ('google', 'github', 'microsoft', 'azure', 'gitlab', 'bitbucket')
    )
);

-- 创建OAuth提供商索引
CREATE INDEX idx_auth_oauth_providers_tenant ON auth_oauth_providers(tenant_id);
CREATE INDEX idx_auth_oauth_providers_enabled ON auth_oauth_providers(is_enabled);

-- 添加注释
COMMENT ON TABLE auth_oauth_providers IS 'OAuth2提供商配置表，支持第三方登录集成';
COMMENT ON COLUMN auth_oauth_providers.encrypted_client_secret IS '客户端密钥，使用pgcrypto加密存储';
COMMENT ON COLUMN auth_oauth_providers.additional_config IS '额外配置信息，如自定义字段映射等';

-- =====================================================
-- 6. OAuth2用户连接表
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_oauth_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider_id UUID NOT NULL REFERENCES auth_oauth_providers(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    external_email VARCHAR(255),
    external_username VARCHAR(255),
    external_name VARCHAR(255),
    external_avatar_url TEXT,
    encrypted_access_token TEXT, -- pgcrypto加密存储
    encrypted_refresh_token TEXT, -- pgcrypto加密存储
    token_expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    profile_data JSONB, -- 完整的用户Profile数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uk_auth_oauth_provider_external UNIQUE(provider_id, external_id)
);

-- 创建OAuth连接索引
CREATE INDEX idx_auth_oauth_connections_user ON auth_oauth_connections(user_id);
CREATE INDEX idx_auth_oauth_connections_provider ON auth_oauth_connections(provider_id);
CREATE INDEX idx_auth_oauth_connections_external ON auth_oauth_connections(external_id);
CREATE INDEX idx_auth_oauth_connections_email ON auth_oauth_connections(external_email);

-- 添加注释
COMMENT ON TABLE auth_oauth_connections IS 'OAuth2用户连接表，存储用户与第三方账号的绑定关系';
COMMENT ON COLUMN auth_oauth_connections.profile_data IS '第三方平台返回的完整用户信息JSON';

-- =====================================================
-- 7. 用户登录历史表
-- =====================================================
CREATE TABLE IF NOT EXISTS auth_login_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    login_type VARCHAR(20) NOT NULL CHECK (login_type IN ('password', 'oauth', 'mfa', 'sso')),
    provider_name VARCHAR(50), -- OAuth登录时的提供商名称
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    geo_location JSONB, -- 地理位置信息
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(200),
    session_id UUID, -- 关联的会话ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建登录历史索引
CREATE INDEX idx_auth_login_history_user ON auth_login_history(user_id);
CREATE INDEX idx_auth_login_history_tenant ON auth_login_history(tenant_id);
CREATE INDEX idx_auth_login_history_created ON auth_login_history(created_at DESC);
CREATE INDEX idx_auth_login_history_success ON auth_login_history(success);
CREATE INDEX idx_auth_login_history_ip ON auth_login_history(ip_address);

-- 添加注释
COMMENT ON TABLE auth_login_history IS '用户登录历史表，记录所有登录尝试用于安全审计';
COMMENT ON COLUMN auth_login_history.login_type IS '登录方式：密码、OAuth、多因素认证、单点登录';
COMMENT ON COLUMN auth_login_history.geo_location IS '地理位置信息JSON，包含国家、城市等';

-- =====================================================
-- 8. 创建触发器函数（自动更新updated_at字段）
-- =====================================================
CREATE OR REPLACE FUNCTION update_auth_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表创建更新时间触发器
CREATE TRIGGER update_auth_roles_updated_at BEFORE UPDATE ON auth_roles
    FOR EACH ROW EXECUTE FUNCTION update_auth_updated_at_column();

CREATE TRIGGER update_auth_users_updated_at BEFORE UPDATE ON auth_users
    FOR EACH ROW EXECUTE FUNCTION update_auth_updated_at_column();

CREATE TRIGGER update_auth_sessions_updated_at BEFORE UPDATE ON auth_user_sessions
    FOR EACH ROW EXECUTE FUNCTION update_auth_updated_at_column();

CREATE TRIGGER update_auth_oauth_providers_updated_at BEFORE UPDATE ON auth_oauth_providers
    FOR EACH ROW EXECUTE FUNCTION update_auth_updated_at_column();

CREATE TRIGGER update_auth_oauth_connections_updated_at BEFORE UPDATE ON auth_oauth_connections
    FOR EACH ROW EXECUTE FUNCTION update_auth_updated_at_column();

-- =====================================================
-- 9. 插入系统默认角色
-- =====================================================
INSERT INTO auth_roles (name, display_name, description, is_system_role, permissions) 
VALUES 
    ('super_admin', '超级管理员', '拥有系统最高权限，可管理所有租户', true, 
     '["tenant:create", "tenant:delete", "system:config", "user:manage_all", "role:manage"]'),
    ('tenant_admin', '租户管理员', '租户级管理员，可管理租户内所有资源', true,
     '["user:create", "user:manage", "provider:manage", "tool:config", "memory:manage", "role:assign"]'),
    ('end_user', '终端用户', '普通用户，可使用AI对话功能', true,
     '["chat:access", "memory:view", "preference:manage", "profile:edit"]')
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- 10. 创建清理函数（定期清理过期数据）
-- =====================================================

-- 清理过期会话的函数
CREATE OR REPLACE FUNCTION cleanup_expired_auth_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_user_sessions 
    WHERE refresh_expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '清理了 % 个过期会话', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 清理过期黑名单令牌的函数
CREATE OR REPLACE FUNCTION cleanup_expired_blacklist_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_token_blacklist
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '清理了 % 个过期黑名单令牌', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 清理旧登录历史的函数（保留90天）
CREATE OR REPLACE FUNCTION cleanup_old_login_history(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    cutoff_date := NOW() - INTERVAL '1 day' * retention_days;
    
    DELETE FROM auth_login_history 
    WHERE created_at < cutoff_date;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '清理了 % 条 % 天前的登录历史', deleted_count, retention_days;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_auth_sessions IS '清理过期的用户会话记录';
COMMENT ON FUNCTION cleanup_expired_blacklist_tokens IS '清理过期的JWT黑名单令牌';
COMMENT ON FUNCTION cleanup_old_login_history IS '清理指定天数前的登录历史，默认保留90天';

-- =====================================================
-- 11. 创建性能优化视图
-- =====================================================

-- 活跃用户统计视图
CREATE VIEW auth_active_users_stats AS
SELECT 
    au.tenant_id,
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE au.is_active = true) as active_users,
    COUNT(*) FILTER (WHERE au.email_verified = true) as verified_users,
    COUNT(*) FILTER (WHERE au.mfa_enabled = true) as mfa_enabled_users,
    COUNT(*) FILTER (WHERE au.last_login_at >= NOW() - INTERVAL '7 days') as weekly_active_users,
    COUNT(*) FILTER (WHERE au.last_login_at >= NOW() - INTERVAL '30 days') as monthly_active_users
FROM auth_users au
GROUP BY au.tenant_id;

COMMENT ON VIEW auth_active_users_stats IS '活跃用户统计视图，按租户聚合用户活跃度指标';

-- 会话统计视图  
CREATE VIEW auth_session_stats AS
SELECT
    aus.tenant_id,
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE aus.is_active = true) as active_sessions,
    COUNT(*) FILTER (WHERE aus.expires_at > NOW()) as valid_sessions,
    AVG(EXTRACT(epoch FROM (aus.last_accessed_at - aus.created_at))/60) as avg_session_duration_minutes
FROM auth_user_sessions aus
GROUP BY aus.tenant_id;

COMMENT ON VIEW auth_session_stats IS '会话统计视图，展示租户级别的会话活跃度';

-- 输出初始化完成信息
SELECT 
    'Auth Service数据库表初始化完成' AS status,
    COUNT(*) AS table_count
FROM information_schema.tables
WHERE table_schema = 'public' 
  AND table_name LIKE 'auth_%';

-- 显示已创建的认证相关表
SELECT 
    schemaname,
    tablename,
    hasindexes,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename LIKE 'auth_%'
ORDER BY tablename;