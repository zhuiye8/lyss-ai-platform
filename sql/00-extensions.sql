-- ================================================================
-- Lyss AI Platform - PostgreSQL扩展和基础配置
-- 
-- 统一数据库架构的第一步：启用必要的扩展和配置
-- 执行顺序：第0步
-- ================================================================

-- 启用UUID生成扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用加密扩展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 启用全文搜索扩展
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 启用GIN索引优化扩展
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- 启用性能监控扩展
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 设置默认时区
SET timezone = 'UTC';

-- 输出扩展加载信息
SELECT 
    '✅ PostgreSQL扩展初始化完成' AS status,
    version() AS postgresql_version,
    current_setting('timezone') AS timezone;