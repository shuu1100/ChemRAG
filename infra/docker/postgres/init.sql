-- ChemRAG PostgreSQL Initialization Script
-- Run once when the container first starts.

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm extension for trigram search on technical identifiers
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify extensions
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');
