-- Seed data for Lyss AI Platform
-- This script inserts initial data for development and testing

-- Insert default super admin tenant
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
        "enabled_models": ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro"],
        "model_rate_limits": {
            "gpt-4": 1000,
            "gpt-3.5-turbo": 5000,
            "claude-3": 1000,
            "gemini-pro": 2000
        },
        "features": {
            "conversation_memory": true,
            "file_upload": true,
            "api_access": true,
            "webhook_integration": true,
            "sso_integration": true,
            "audit_logs": true,
            "advanced_analytics": true
        },
        "custom_branding": {
            "logo_url": "/assets/lyss-logo.png",
            "primary_color": "#1890ff",
            "company_name": "Lyss AI Technologies"
        }
    }'::jsonb
) ON CONFLICT (tenant_id) DO NOTHING;

-- Insert demo tenant for testing
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
        "enabled_models": ["gpt-4", "gpt-3.5-turbo"],
        "model_rate_limits": {
            "gpt-4": 100,
            "gpt-3.5-turbo": 500
        },
        "features": {
            "conversation_memory": true,
            "file_upload": true,
            "api_access": true,
            "webhook_integration": false,
            "sso_integration": false,
            "audit_logs": true,
            "advanced_analytics": true
        }
    }'::jsonb
) ON CONFLICT (tenant_id) DO NOTHING;

-- Insert super admin user
INSERT INTO users (
    user_id,
    tenant_id,
    email,
    username,
    password_hash,
    first_name,
    last_name,
    status,
    roles,
    preferences
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'admin@lyss.ai',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3Qb.9/2.G.',  -- password: admin123
    'System',
    'Administrator',
    'active',
    '["super_admin", "tenant_admin"]'::jsonb,
    '{
        "theme": "light",
        "language": "en",
        "timezone": "UTC",
        "notifications": {
            "email": true,
            "push": true,
            "browser": true
        },
        "ai_settings": {
            "default_model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
            "use_memory": true
        }
    }'::jsonb
) ON CONFLICT (user_id) DO NOTHING;

-- Insert demo tenant admin user
INSERT INTO users (
    user_id,
    tenant_id,
    email,
    username,
    password_hash,
    first_name,
    last_name,
    status,
    roles,
    preferences
) VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000002',
    'demo@example.com',
    'demo_admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3Qb.9/2.G.',  -- password: admin123
    'Demo',
    'Admin',
    'active',
    '["tenant_admin"]'::jsonb,
    '{
        "theme": "light",
        "language": "en",
        "timezone": "UTC",
        "notifications": {
            "email": true,
            "push": false,
            "browser": true
        },
        "ai_settings": {
            "default_model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1500,
            "use_memory": true
        }
    }'::jsonb
) ON CONFLICT (user_id) DO NOTHING;

-- Insert demo end user
INSERT INTO users (
    user_id,
    tenant_id,
    email,
    username,
    password_hash,
    first_name,
    last_name,
    status,
    roles,
    preferences
) VALUES (
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000002',
    'user@example.com',
    'demo_user',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3Qb.9/2.G.',  -- password: admin123
    'Demo',
    'User',
    'active',
    '["end_user"]'::jsonb,
    '{
        "theme": "light",
        "language": "en",
        "timezone": "UTC",
        "notifications": {
            "email": false,
            "push": false,
            "browser": true
        },
        "ai_settings": {
            "default_model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000,
            "use_memory": true
        }
    }'::jsonb
) ON CONFLICT (user_id) DO NOTHING;

-- Insert sample AI credentials (encrypted)
INSERT INTO ai_credentials (
    credential_id,
    tenant_id,
    provider_name,
    provider_type,
    display_name,
    api_key,
    base_url,
    model_mappings,
    rate_limits,
    is_active
) VALUES 
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000001',
    'OpenAI',
    'openai',
    'OpenAI GPT Models',
    'sk-sample-key-not-real-change-this-in-production',
    'https://api.openai.com/v1',
    '{
        "gpt-4": {
            "model_name": "gpt-4",
            "model_type": "chat",
            "context_window": 8192,
            "max_tokens": 4096,
            "supports_streaming": true,
            "supports_function_calling": true
        },
        "gpt-3.5-turbo": {
            "model_name": "gpt-3.5-turbo",
            "model_type": "chat",
            "context_window": 4096,
            "max_tokens": 2048,
            "supports_streaming": true,
            "supports_function_calling": true
        }
    }'::jsonb,
    '{
        "requests_per_minute": 3500,
        "tokens_per_minute": 90000
    }'::jsonb,
    true
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    'OpenAI',
    'openai',
    'Demo OpenAI Access',
    'sk-demo-key-not-real-change-this-in-production',
    'https://api.openai.com/v1',
    '{
        "gpt-3.5-turbo": {
            "model_name": "gpt-3.5-turbo",
            "model_type": "chat",
            "context_window": 4096,
            "max_tokens": 2048,
            "supports_streaming": true,
            "supports_function_calling": true
        }
    }'::jsonb,
    '{
        "requests_per_minute": 500,
        "tokens_per_minute": 15000
    }'::jsonb,
    true
);

-- Insert sample conversation for demo user
INSERT INTO conversations (
    conversation_id,
    tenant_id,
    user_id,
    title,
    summary,
    status,
    metadata
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000003',
    'Welcome to Lyss AI Platform',
    'Initial conversation introducing the platform capabilities',
    'active',
    '{
        "tags": ["welcome", "introduction"],
        "priority": "normal",
        "model_used": "gpt-3.5-turbo"
    }'::jsonb
) ON CONFLICT (conversation_id) DO NOTHING;

-- Insert sample messages
INSERT INTO messages (
    message_id,
    conversation_id,
    tenant_id,
    role,
    content,
    content_type,
    metadata
) VALUES 
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    'user',
    'Hello! I''m excited to try out the Lyss AI Platform. Can you tell me what you can help me with?',
    'text',
    '{}'::jsonb
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    'assistant',
    'Welcome to Lyss AI Platform! I''m here to help you with a wide variety of tasks. Here are some things I can assist you with:

1. **Answering Questions**: I can provide information on virtually any topic
2. **Writing & Editing**: Help with emails, documents, creative writing, and more
3. **Analysis & Problem Solving**: Break down complex problems and provide solutions
4. **Code & Technical Help**: Assist with programming, debugging, and technical explanations
5. **Learning & Education**: Explain concepts, help with homework, or teach new skills

The platform also remembers our conversations, so I can build on what we''ve discussed before. What would you like to explore first?',
    'text',
    '{
        "model": "gpt-3.5-turbo",
        "provider": "openai",
        "usage": {
            "prompt_tokens": 45,
            "completion_tokens": 156,
            "total_tokens": 201
        }
    }'::jsonb
);

-- Insert sample usage statistics
INSERT INTO usage_statistics (
    tenant_id,
    user_id,
    date,
    hour,
    api_calls,
    tokens_consumed,
    cost_usd,
    provider_stats
) VALUES 
(
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000003',
    CURRENT_DATE,
    EXTRACT(HOUR FROM CURRENT_TIMESTAMP)::INTEGER,
    1,
    201,
    0.0003,
    '{
        "openai": {
            "api_calls": 1,
            "tokens": 201,
            "cost_usd": 0.0003
        }
    }'::jsonb
);

-- Log successful seed data insertion
DO $$
BEGIN
    RAISE NOTICE 'Seed data inserted successfully for Lyss AI Platform';
    RAISE NOTICE 'Default admin user: admin@lyss.ai / admin123';
    RAISE NOTICE 'Demo tenant admin: demo@example.com / admin123';
    RAISE NOTICE 'Demo end user: user@example.com / admin123';
END
$$;