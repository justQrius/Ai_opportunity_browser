-- Initialize AI Opportunity Browser Database
-- This script runs when the PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database user (if needed)
-- Note: The main database and user are created via environment variables

-- Set timezone
SET timezone = 'UTC';