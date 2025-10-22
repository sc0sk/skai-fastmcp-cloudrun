-- Initialize hansard database with pgvector and IAM permissions
-- Run this via: gcloud sql connect hansard-db-v2 --user=postgres --database=hansard

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant IAM permissions to Cloud Run service account
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";
GRANT CREATE ON SCHEMA public TO "666924716777-compute@developer";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";

-- Grant default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "666924716777-compute@developer";

-- Create speeches table (full text storage)
CREATE TABLE IF NOT EXISTS speeches (
    speech_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    title TEXT NOT NULL,
    speaker TEXT NOT NULL,
    party TEXT,
    chamber TEXT,
    electorate TEXT,
    state TEXT,
    date DATE NOT NULL,
    hansard_reference TEXT,
    full_text TEXT NOT NULL,
    word_count INTEGER,
    content_hash TEXT UNIQUE,
    topic_tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create speech_chunks table (vector embeddings)
CREATE TABLE IF NOT EXISTS speech_chunks (
    chunk_id TEXT PRIMARY KEY,
    speech_id TEXT NOT NULL REFERENCES speeches(speech_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_size INTEGER NOT NULL,
    embedding vector(768),
    speaker TEXT NOT NULL,
    party TEXT,
    chamber TEXT,
    state TEXT,
    date DATE NOT NULL,
    hansard_reference TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(speech_id, chunk_index)
);

-- Create HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS speech_chunks_embedding_idx
ON speech_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS speech_chunks_speech_id_idx ON speech_chunks(speech_id);
CREATE INDEX IF NOT EXISTS speech_chunks_speaker_idx ON speech_chunks(speaker);
CREATE INDEX IF NOT EXISTS speech_chunks_date_idx ON speech_chunks(date);
CREATE INDEX IF NOT EXISTS speeches_speaker_idx ON speeches(speaker);
CREATE INDEX IF NOT EXISTS speeches_date_idx ON speeches(date);

-- Verify pgvector extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Verify tables
\dt

-- Verify IAM permissions
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = '666924716777-compute@developer'
AND table_schema = 'public'
LIMIT 10;
