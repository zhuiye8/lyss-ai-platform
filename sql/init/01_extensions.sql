-- Enable required PostgreSQL extensions
-- This script sets up the necessary extensions for Lyss AI Platform

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable cryptographic functions for encryption
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable case-insensitive text operations
CREATE EXTENSION IF NOT EXISTS "citext";

-- Enable vector similarity search (if available)
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable full-text search with better language support
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Enable trigram similarity matching
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Log successful extension installation
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL extensions installed successfully for Lyss AI Platform';
END
$$;