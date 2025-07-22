# 数据库架构设计 (2025-01-21 重构版)

## 📋 文档概述

基于深度调研Dify等成熟AI平台和Provider Service成功实践，采用**统一数据库架构**，支持生产级多租户隔离。

---

## 🗄️ 数据库架构方案

### **核心设计原则**
- **统一数据库架构** - 所有微服务共享同一PostgreSQL数据库实例
- **表级多租户隔离** - 通过tenant_id实现数据隔离，支持Row Level Security  
- **服务模块化** - 每个服务拥有独立的表命名空间，便于管理和扩展
- **ACID事务保障** - 避免分布式事务复杂性，确保数据一致性

### **架构决策依据**
1. **Dify案例验证** - 成熟AI平台使用统一数据库+多租户设计
2. **Provider Service成功** - 已完成的Provider Service验证了此架构的可行性  
3. **简化运维** - 统一数据库降低部署复杂度和维护成本
4. **数据一致性** - 避免跨服务数据同步问题，支持复杂业务事务

### **数据库结构**
```sql
-- 统一数据库：lyss_db
-- 各服务通过表前缀区分：
-- - auth_* : 认证服务表
-- - provider_* : 供应商服务表  
-- - chat_* : 对话服务表
-- - memory_* : 记忆服务表
-- - tenant_* : 租户管理表
```

---

## 🔐 认证服务表结构 (auth_*)

### **用户表**
```sql
CREATE TABLE auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100), 
    role_id UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255), -- TOTP密钥，加密存储
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 多租户唯一约束
    CONSTRAINT uk_auth_users_tenant_email UNIQUE(tenant_id, email),
    CONSTRAINT uk_auth_users_tenant_username UNIQUE(tenant_id, username)
);

CREATE INDEX idx_auth_users_tenant_id ON auth_users(tenant_id);
CREATE INDEX idx_auth_users_email ON auth_users(email);
CREATE INDEX idx_auth_users_role_id ON auth_users(role_id);
CREATE INDEX idx_auth_users_active ON auth_users(is_active);
```

### **用户会话表**
```sql  
CREATE TABLE auth_user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    refresh_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    refresh_expires_at TIMESTAMP NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_auth_sessions_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
);

CREATE INDEX idx_auth_sessions_user_id ON auth_user_sessions(user_id);
CREATE INDEX idx_auth_sessions_token ON auth_user_sessions(session_token);  
CREATE INDEX idx_auth_sessions_active ON auth_user_sessions(is_active);
CREATE INDEX idx_auth_sessions_expires ON auth_user_sessions(expires_at);
```

### **OAuth2集成表**
```sql
CREATE TABLE auth_oauth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider_name VARCHAR(50) NOT NULL, -- google, github, microsoft
    client_id VARCHAR(255) NOT NULL,
    encrypted_client_secret TEXT NOT NULL, -- pgcrypto加密
    redirect_uri VARCHAR(500) NOT NULL,
    scopes TEXT[] DEFAULT ARRAY['openid', 'profile', 'email'],
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT uk_auth_oauth_tenant_provider UNIQUE(tenant_id, provider_name)
);

CREATE TABLE auth_oauth_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    provider_id UUID NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    external_email VARCHAR(255),
    external_username VARCHAR(255),
    access_token TEXT, -- 加密存储
    refresh_token TEXT, -- 加密存储  
    token_expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_auth_oauth_user FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_auth_oauth_provider FOREIGN KEY (provider_id) REFERENCES auth_oauth_providers(id) ON DELETE CASCADE,
    CONSTRAINT uk_auth_oauth_provider_external UNIQUE(provider_id, external_id)
);
```

---

## 👥 租户管理表结构 (tenant_*)

### **租户表** 
```sql
CREATE TABLE tenant_organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'inactive')),
    subscription_plan VARCHAR(50) DEFAULT 'basic',
    max_users INTEGER DEFAULT 10,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tenant_orgs_slug ON tenant_organizations(slug);
CREATE INDEX idx_tenant_orgs_status ON tenant_organizations(status);
```

### **用户表**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100),
    password_hash TEXT NOT NULL,
    full_name VARCHAR(200),
    avatar_url TEXT,
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive, suspended
    role VARCHAR(20) DEFAULT 'end_user',  -- super_admin, tenant_admin, end_user
    email_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(tenant_id, status);
```

### **用户群组表**
```sql
CREATE TABLE user_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(tenant_id, name)
);

CREATE TABLE user_group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES user_groups(id),
    user_id UUID NOT NULL REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'member',  -- admin, member
    joined_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(group_id, user_id)
);
```

---

## 🔌 供应商服务数据库 (lyss_provider_db)

### **供应商类型定义表**
```sql
CREATE TABLE provider_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- openai, anthropic, deepseek, etc.
    display_name VARCHAR(100) NOT NULL,
    base_url TEXT,
    supported_models JSONB DEFAULT '[]',
    api_format VARCHAR(20) DEFAULT 'openai',  -- openai, anthropic, custom
    status VARCHAR(20) DEFAULT 'active'
);

-- 预置供应商类型
INSERT INTO provider_types (name, display_name, base_url, api_format) VALUES
('openai', 'OpenAI', 'https://api.openai.com', 'openai'),
('anthropic', 'Anthropic', 'https://api.anthropic.com', 'anthropic'),
('deepseek', 'DeepSeek', 'https://api.deepseek.com', 'openai'),
('azure-openai', 'Azure OpenAI', NULL, 'openai'),
('zhipu', '智谱AI', 'https://open.bigmodel.cn', 'openai');
```

### **Channel表（基于One-API设计）**
```sql
CREATE TABLE provider_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,  -- 租户ID
    name VARCHAR(100) NOT NULL,  -- 显示名称
    type INTEGER NOT NULL REFERENCES provider_types(id),  -- 供应商类型
    
    -- One-API标准字段
    key TEXT NOT NULL,  -- 加密的API密钥
    priority INTEGER DEFAULT 1,  -- 优先级 (1-100)
    weight INTEGER DEFAULT 1,   -- 权重 (负载均衡)
    status INTEGER DEFAULT 1,   -- 1=启用, 2=禁用, 3=错误
    
    -- 配额管理
    quota BIGINT DEFAULT -1,    -- -1表示无限制
    used_quota BIGINT DEFAULT 0,
    rate_limit INTEGER DEFAULT 100,  -- 每分钟请求限制
    
    -- 配置范围
    config_scope VARCHAR(20) DEFAULT 'personal',  -- personal, group, tenant
    owner_id UUID,  -- 个人配置时的用户ID
    group_id UUID,  -- 群组配置时的群组ID
    
    -- 模型配置
    models JSONB DEFAULT '[]',  -- 支持的模型列表
    model_mapping JSONB DEFAULT '{}',  -- 模型映射配置
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 确保租户内名称唯一
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_channels_tenant_scope ON provider_channels(tenant_id, config_scope);
CREATE INDEX idx_channels_status ON provider_channels(status);
```

### **Token表（用户访问令牌）**
```sql
CREATE TABLE user_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,  -- Token名称
    key TEXT UNIQUE NOT NULL,    -- 实际Token值
    
    -- 权限控制
    allowed_channels JSONB DEFAULT '[]',  -- 允许使用的Channel ID列表
    allowed_models JSONB DEFAULT '[]',    -- 允许使用的模型列表
    
    -- 配额管理
    quota BIGINT DEFAULT -1,     -- -1表示无限制
    used_quota BIGINT DEFAULT 0,
    rate_limit INTEGER DEFAULT 60,  -- 每分钟请求限制
    
    -- 状态管理
    status INTEGER DEFAULT 1,    -- 1=启用, 2=禁用, 3=过期
    expires_at TIMESTAMP,        -- 过期时间
    last_used_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tokens_tenant_user ON user_tokens(tenant_id, user_id);
CREATE INDEX idx_tokens_key ON user_tokens(key);
```

---

## 💬 对话服务数据库 (lyss_chat_db)

### **对话会话表**
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    title VARCHAR(200) NOT NULL,
    
    -- 模型配置
    model_name VARCHAR(100),
    provider_channel_id UUID,  -- 使用的Channel ID
    
    -- 对话配置
    system_prompt TEXT,
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4000,
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    message_count INTEGER DEFAULT 0,
    token_usage INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_tenant_user ON conversations(tenant_id, user_id);
CREATE INDEX idx_conversations_status ON conversations(status);
```

### **对话消息表**
```sql
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- 消息内容
    role VARCHAR(20) NOT NULL,  -- user, assistant, system, tool
    content TEXT NOT NULL,
    
    -- 元数据
    token_count INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    response_time_ms INTEGER,
    
    -- 工具调用相关
    tool_calls JSONB,
    tool_call_id VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id);
CREATE INDEX idx_messages_created_at ON conversation_messages(created_at);
```

### **对话总结表**
```sql
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    summary_type VARCHAR(20) DEFAULT 'auto',  -- auto, manual
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🧠 记忆服务数据库 (lyss_memory_db)

### **用户记忆表（基于Mem0AI设计）**
```sql
CREATE TABLE user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- 记忆内容
    memory_text TEXT NOT NULL,
    memory_hash VARCHAR(64) NOT NULL,  -- 用于去重
    
    -- 向量检索
    embedding_id VARCHAR(255),  -- Qdrant中的向量ID
    relevance_score FLOAT DEFAULT 0.0,
    
    -- 记忆分类
    memory_type VARCHAR(50) DEFAULT 'conversation',  -- conversation, preference, fact
    memory_category VARCHAR(50),  -- personal, work, hobby, etc.
    
    -- 来源信息
    source_type VARCHAR(20) DEFAULT 'chat',  -- chat, import, manual
    source_id UUID,  -- 来源对话ID或其他来源ID
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    importance_score INTEGER DEFAULT 50,  -- 1-100，重要程度
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 确保同一用户的记忆内容不重复
    UNIQUE(tenant_id, user_id, memory_hash)
);

CREATE INDEX idx_memories_tenant_user ON user_memories(tenant_id, user_id);
CREATE INDEX idx_memories_type ON user_memories(memory_type);
CREATE INDEX idx_memories_status ON user_memories(status);
```

### **记忆关联表**
```sql
CREATE TABLE memory_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES user_memories(id) ON DELETE CASCADE,
    related_memory_id UUID NOT NULL REFERENCES user_memories(id) ON DELETE CASCADE,
    association_type VARCHAR(50) DEFAULT 'similar',  -- similar, related, opposite
    strength FLOAT DEFAULT 0.5,  -- 关联强度 0-1
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(memory_id, related_memory_id)
);
```

---

## 🔧 数据库优化配置

### **性能优化**
```sql
-- 启用性能相关扩展
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 模糊搜索
CREATE EXTENSION IF NOT EXISTS btree_gin; -- 复合索引优化

-- 分区表配置（对于大数据量表）
-- 按月分区对话消息表
CREATE TABLE conversation_messages_y2025m01 
PARTITION OF conversation_messages 
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### **备份策略**
```bash
# 每日增量备份脚本
pg_dump --format=custom --no-owner --no-privileges \
  --exclude-table-data=conversation_messages \
  lyss_user_db > backup_user_$(date +%Y%m%d).dump

# 重要表实时备份
pg_dump --format=custom --table=users --table=tenants \
  lyss_user_db > critical_$(date +%Y%m%d_%H%M).dump
```