-- Initialize LangChain-compatible schema for hansard_speeches table
-- PostgreSQL 15 with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create hansard_speeches table with LangChain schema
CREATE TABLE IF NOT EXISTS hansard_speeches (
    langchain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    langchain_metadata JSONB DEFAULT '{}'::jsonb,
    speaker VARCHAR(200),
    party VARCHAR(100),
    chamber VARCHAR(50),
    date DATE,
    speech_type VARCHAR(100),
    electorate VARCHAR(100),
    speaker_id VARCHAR(20),
    utterance_id VARCHAR(100),
    debate TEXT
);

-- Create HNSW vector index for similarity search
CREATE INDEX IF NOT EXISTS hansard_speeches_embedding_idx
ON hansard_speeches
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);

-- Create metadata indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_speaker ON hansard_speeches(speaker);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_party ON hansard_speeches(party);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_chamber ON hansard_speeches(chamber);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_date ON hansard_speeches(date);
