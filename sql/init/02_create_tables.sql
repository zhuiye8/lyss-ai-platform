-- Create tables for Lyss AI Platform
-- This script creates the core database schema

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_name VARCHAR(255) NOT NULL,
    tenant_slug VARCHAR(100) UNIQUE NOT NULL,
    
    -- Contact information
    contact_email VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    company_name VARCHAR(255),
    
    -- Status and plan
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'suspended', 'deleted', 'trial')),
    subscription_plan VARCHAR(20) DEFAULT 'free' NOT NULL 
        CHECK (subscription_plan IN ('free', 'basic', 'professional', 'enterprise')),
    
    -- Configuration (JSONB for flexible schema)
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Database configuration (encrypted)
    database_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Metadata
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for tenants
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(tenant_slug);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_plan ON tenants(subscription_plan);
CREATE INDEX IF NOT EXISTS idx_tenants_config ON tenants USING gin(config);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    
    -- Authentication
    email CITEXT NOT NULL,
    username VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    profile_picture VARCHAR(500),
    
    -- Status and roles
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'inactive', 'suspended', 'deleted')),
    roles JSONB NOT NULL DEFAULT '["end_user"]'::jsonb,
    
    -- Authentication tracking
    last_login_at TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    -- Preferences
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Unique constraints
    UNIQUE(email, tenant_id),
    UNIQUE(username, tenant_id)
);

-- Create indexes for users
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_roles ON users USING gin(roles);

-- Create AI credentials table (for storing encrypted API keys)
CREATE TABLE IF NOT EXISTS ai_credentials (
    credential_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    
    -- Provider info
    provider_name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    
    -- Credentials (encrypted using pgcrypto)
    api_key TEXT NOT NULL,
    base_url VARCHAR(500),
    
    -- Configuration
    model_mappings JSONB NOT NULL DEFAULT '{}'::jsonb,
    rate_limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Status
    is_active BOOLEAN DEFAULT true NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for AI credentials
CREATE INDEX IF NOT EXISTS idx_ai_credentials_tenant ON ai_credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_credentials_provider ON ai_credentials(provider_type);
CREATE INDEX IF NOT EXISTS idx_ai_credentials_active ON ai_credentials(is_active);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Content
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' NOT NULL 
        CHECK (status IN ('active', 'archived', 'deleted')),
    
    -- Metadata
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Statistics
    message_count INTEGER DEFAULT 0 NOT NULL,
    last_message_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for conversations
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    
    -- Content
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text' NOT NULL,
    
    -- Metadata
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Attachments
    attachments JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for messages
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_tenant ON messages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- Create audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    
    -- Result
    result VARCHAR(20) NOT NULL CHECK (result IN ('success', 'failure', 'error')),
    
    -- Details
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Context
    ip_address INET,
    user_agent VARCHAR(500),
    
    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- Create usage statistics table
CREATE TABLE IF NOT EXISTS usage_statistics (
    stat_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    
    -- Time period
    date DATE NOT NULL,
    hour INTEGER CHECK (hour >= 0 AND hour <= 23),
    
    -- Usage metrics
    api_calls INTEGER DEFAULT 0 NOT NULL,
    tokens_consumed INTEGER DEFAULT 0 NOT NULL,
    cost_usd DECIMAL(10,4) DEFAULT 0 NOT NULL,
    
    -- Provider breakdown
    provider_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Unique constraint for time periods
    UNIQUE(tenant_id, user_id, date, hour)
);

-- Create indexes for usage statistics
CREATE INDEX IF NOT EXISTS idx_usage_stats_tenant_date ON usage_statistics(tenant_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_usage_stats_user_date ON usage_statistics(user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_usage_stats_date ON usage_statistics(date DESC);

-- Create API keys table (for programmatic access)
CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    
    -- Key details
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 hash of the actual key
    key_prefix VARCHAR(10) NOT NULL, -- First few characters for identification
    
    -- Permissions and limits
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    rate_limit INTEGER, -- requests per minute
    
    -- Status
    is_active BOOLEAN DEFAULT true NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for API keys
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- Log successful table creation
DO $$
BEGIN
    RAISE NOTICE 'Core tables created successfully for Lyss AI Platform';
END
$$;