-- Lyss AI Platform - PostgreSQL 扩展安装
-- 此脚本安装项目所需的PostgreSQL扩展

-- 启用UUID生成扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用加密扩展（用于敏感数据加密）
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 启用向量扩展（用于AI嵌入向量存储）
CREATE EXTENSION IF NOT EXISTS "vector";

-- 启用CITEXT扩展（用于大小写不敏感的文本）
CREATE EXTENSION IF NOT EXISTS "citext";

-- 启用性能统计扩展
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 启用全文搜索扩展
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建加密密钥管理函数
CREATE OR REPLACE FUNCTION get_encryption_key(key_name TEXT)
RETURNS TEXT AS $$
BEGIN
    -- 从环境变量或配置中获取加密密钥
    -- 在生产环境中应该使用更安全的密钥管理方式
    RETURN COALESCE(
        current_setting('lyss.encryption_key_' || key_name, true),
        'default_dev_key_' || key_name -- 仅用于开发环境
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建通用加密函数
CREATE OR REPLACE FUNCTION encrypt_data(data TEXT, key_name TEXT DEFAULT 'default')
RETURNS TEXT AS $$
BEGIN
    IF data IS NULL THEN
        RETURN NULL;
    END IF;
    
    -- 使用pgcrypto进行对称加密
    RETURN encode(
        pgp_sym_encrypt(
            data, 
            get_encryption_key(key_name)
        ), 
        'base64'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建通用解密函数
CREATE OR REPLACE FUNCTION decrypt_data(encrypted_data TEXT, key_name TEXT DEFAULT 'default')
RETURNS TEXT AS $$
BEGIN
    IF encrypted_data IS NULL THEN
        RETURN NULL;
    END IF;
    
    -- 使用pgcrypto进行对称解密
    RETURN pgp_sym_decrypt(
        decode(encrypted_data, 'base64'),
        get_encryption_key(key_name)
    );
EXCEPTION
    WHEN others THEN
        -- 解密失败时返回NULL
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建租户上下文设置函数
CREATE OR REPLACE FUNCTION set_tenant_context(tenant_uuid UUID)
RETURNS void AS $$
BEGIN
    -- 设置当前租户ID到会话变量
    PERFORM set_config('lyss.current_tenant_id', tenant_uuid::text, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建获取当前租户ID的函数
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID AS $$
BEGIN
    RETURN current_setting('lyss.current_tenant_id', true)::UUID;
EXCEPTION
    WHEN others THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 输出成功消息
DO $$
BEGIN
    RAISE NOTICE 'Lyss AI Platform - PostgreSQL扩展和加密函数安装成功';
END
$$;