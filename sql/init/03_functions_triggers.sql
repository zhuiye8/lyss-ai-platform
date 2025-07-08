-- Create functions and triggers for Lyss AI Platform
-- This script sets up database functions, triggers, and automation

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_tenants_updated_at 
    BEFORE UPDATE ON tenants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_credentials_updated_at 
    BEFORE UPDATE ON ai_credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at 
    BEFORE UPDATE ON conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at 
    BEFORE UPDATE ON messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usage_statistics_updated_at 
    BEFORE UPDATE ON usage_statistics 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at 
    BEFORE UPDATE ON api_keys 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to encrypt API keys before storing
CREATE OR REPLACE FUNCTION encrypt_api_key()
RETURNS TRIGGER AS $$
BEGIN
    -- Only encrypt if the key is not already encrypted
    IF NEW.api_key IS NOT NULL AND NEW.api_key != OLD.api_key THEN
        NEW.api_key = crypt(NEW.api_key, gen_salt('bf'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to encrypt API keys
CREATE TRIGGER encrypt_ai_credentials_api_key
    BEFORE INSERT OR UPDATE ON ai_credentials
    FOR EACH ROW EXECUTE FUNCTION encrypt_api_key();

-- Function to update conversation statistics
CREATE OR REPLACE FUNCTION update_conversation_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Update message count and last message time
        UPDATE conversations 
        SET message_count = message_count + 1,
            last_message_at = NEW.created_at
        WHERE conversation_id = NEW.conversation_id;
        
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- Update message count
        UPDATE conversations 
        SET message_count = GREATEST(message_count - 1, 0)
        WHERE conversation_id = OLD.conversation_id;
        
        -- Update last message time if this was the last message
        UPDATE conversations 
        SET last_message_at = (
            SELECT MAX(created_at) 
            FROM messages 
            WHERE conversation_id = OLD.conversation_id
        )
        WHERE conversation_id = OLD.conversation_id;
        
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update conversation statistics
CREATE TRIGGER update_conversation_message_stats
    AFTER INSERT OR DELETE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_conversation_stats();

-- Function to log user activities to audit log
CREATE OR REPLACE FUNCTION log_user_activity()
RETURNS TRIGGER AS $$
DECLARE
    action_type VARCHAR(100);
    resource_type VARCHAR(100);
BEGIN
    -- Determine action and resource type based on table
    CASE TG_TABLE_NAME
        WHEN 'users' THEN
            resource_type := 'user';
            IF TG_OP = 'INSERT' THEN action_type := 'create';
            ELSIF TG_OP = 'UPDATE' THEN action_type := 'update';
            ELSIF TG_OP = 'DELETE' THEN action_type := 'delete';
            END IF;
        WHEN 'conversations' THEN
            resource_type := 'conversation';
            IF TG_OP = 'INSERT' THEN action_type := 'create';
            ELSIF TG_OP = 'UPDATE' THEN action_type := 'update';
            ELSIF TG_OP = 'DELETE' THEN action_type := 'delete';
            END IF;
        WHEN 'ai_credentials' THEN
            resource_type := 'ai_credential';
            IF TG_OP = 'INSERT' THEN action_type := 'create';
            ELSIF TG_OP = 'UPDATE' THEN action_type := 'update';
            ELSIF TG_OP = 'DELETE' THEN action_type := 'delete';
            END IF;
        ELSE
            RETURN COALESCE(NEW, OLD);
    END CASE;
    
    -- Insert audit log entry
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (
            tenant_id, user_id, event_type, action, resource_type, 
            resource_id, result, details
        ) VALUES (
            OLD.tenant_id, 
            CASE WHEN TG_TABLE_NAME = 'users' THEN OLD.user_id ELSE NULL END,
            'database_operation',
            action_type,
            resource_type,
            CASE 
                WHEN TG_TABLE_NAME = 'users' THEN OLD.user_id::TEXT
                WHEN TG_TABLE_NAME = 'conversations' THEN OLD.conversation_id::TEXT
                WHEN TG_TABLE_NAME = 'ai_credentials' THEN OLD.credential_id::TEXT
            END,
            'success',
            jsonb_build_object('table', TG_TABLE_NAME, 'operation', TG_OP)
        );
        RETURN OLD;
    ELSE
        INSERT INTO audit_logs (
            tenant_id, user_id, event_type, action, resource_type, 
            resource_id, result, details
        ) VALUES (
            NEW.tenant_id, 
            CASE WHEN TG_TABLE_NAME = 'users' THEN NEW.user_id ELSE NULL END,
            'database_operation',
            action_type,
            resource_type,
            CASE 
                WHEN TG_TABLE_NAME = 'users' THEN NEW.user_id::TEXT
                WHEN TG_TABLE_NAME = 'conversations' THEN NEW.conversation_id::TEXT
                WHEN TG_TABLE_NAME = 'ai_credentials' THEN NEW.credential_id::TEXT
            END,
            'success',
            jsonb_build_object('table', TG_TABLE_NAME, 'operation', TG_OP)
        );
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create audit triggers for key tables
CREATE TRIGGER audit_users_activity
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION log_user_activity();

CREATE TRIGGER audit_conversations_activity
    AFTER INSERT OR UPDATE OR DELETE ON conversations
    FOR EACH ROW EXECUTE FUNCTION log_user_activity();

CREATE TRIGGER audit_ai_credentials_activity
    AFTER INSERT OR UPDATE OR DELETE ON ai_credentials
    FOR EACH ROW EXECUTE FUNCTION log_user_activity();

-- Function to validate tenant configuration
CREATE OR REPLACE FUNCTION validate_tenant_config()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate max_users
    IF (NEW.config->>'max_users')::INTEGER <= 0 THEN
        RAISE EXCEPTION 'max_users must be greater than 0';
    END IF;
    
    -- Validate max_api_calls_per_month
    IF (NEW.config->>'max_api_calls_per_month')::INTEGER < 0 THEN
        RAISE EXCEPTION 'max_api_calls_per_month must be non-negative';
    END IF;
    
    -- Validate subscription plan limits
    CASE NEW.subscription_plan
        WHEN 'free' THEN
            IF (NEW.config->>'max_users')::INTEGER > 5 THEN
                RAISE EXCEPTION 'Free plan limited to 5 users';
            END IF;
        WHEN 'basic' THEN
            IF (NEW.config->>'max_users')::INTEGER > 25 THEN
                RAISE EXCEPTION 'Basic plan limited to 25 users';
            END IF;
        WHEN 'professional' THEN
            IF (NEW.config->>'max_users')::INTEGER > 100 THEN
                RAISE EXCEPTION 'Professional plan limited to 100 users';
            END IF;
        -- Enterprise has no limits
    END CASE;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to validate tenant configuration
CREATE TRIGGER validate_tenant_config_trigger
    BEFORE INSERT OR UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION validate_tenant_config();

-- Function to clean up old audit logs (to be run by cron job)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_logs 
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 day' * retention_days;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to aggregate usage statistics
CREATE OR REPLACE FUNCTION aggregate_usage_stats(target_date DATE DEFAULT CURRENT_DATE)
RETURNS VOID AS $$
BEGIN
    -- Aggregate hourly stats into daily stats (if needed)
    INSERT INTO usage_statistics (tenant_id, user_id, date, api_calls, tokens_consumed, cost_usd, provider_stats)
    SELECT 
        tenant_id,
        user_id,
        target_date,
        SUM(api_calls),
        SUM(tokens_consumed),
        SUM(cost_usd),
        jsonb_object_agg(
            provider, 
            jsonb_build_object(
                'api_calls', provider_api_calls,
                'tokens', provider_tokens,
                'cost_usd', provider_cost
            )
        )
    FROM (
        SELECT 
            tenant_id,
            user_id,
            jsonb_each_text(provider_stats) AS provider_stat,
            SUM(api_calls) as api_calls,
            SUM(tokens_consumed) as tokens_consumed,
            SUM(cost_usd) as cost_usd
        FROM usage_statistics 
        WHERE date = target_date AND hour IS NOT NULL
        GROUP BY tenant_id, user_id
    ) hourly_stats,
    LATERAL (
        SELECT 
            provider_stat.key as provider,
            (provider_stat.value::jsonb->>'api_calls')::INTEGER as provider_api_calls,
            (provider_stat.value::jsonb->>'tokens')::INTEGER as provider_tokens,
            (provider_stat.value::jsonb->>'cost_usd')::DECIMAL as provider_cost
    ) provider_breakdown
    GROUP BY tenant_id, user_id
    ON CONFLICT (tenant_id, user_id, date, hour) DO UPDATE SET
        api_calls = EXCLUDED.api_calls,
        tokens_consumed = EXCLUDED.tokens_consumed,
        cost_usd = EXCLUDED.cost_usd,
        provider_stats = EXCLUDED.provider_stats,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Function to generate tenant database configuration
CREATE OR REPLACE FUNCTION generate_tenant_db_config(tenant_slug VARCHAR)
RETURNS JSONB AS $$
DECLARE
    db_config JSONB;
BEGIN
    -- Generate database configuration for tenant
    db_config := jsonb_build_object(
        'database_name', 'lyss_tenant_' || tenant_slug,
        'schema_name', 'tenant_' || replace(tenant_slug, '-', '_'),
        'connection_pool_size', 5,
        'max_connections', 10
    );
    
    RETURN db_config;
END;
$$ LANGUAGE plpgsql;

-- Log successful function and trigger creation
DO $$
BEGIN
    RAISE NOTICE 'Database functions and triggers created successfully for Lyss AI Platform';
END
$$;