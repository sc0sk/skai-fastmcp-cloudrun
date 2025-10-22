-- Migration: Add chunk_id column to speech_chunks table
-- This fixes the "Id column, chunk_id, does not exist" error

-- Check if column already exists before adding
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'speech_chunks'
        AND column_name = 'chunk_id'
    ) THEN
        -- Add chunk_id column as TEXT
        ALTER TABLE speech_chunks ADD COLUMN chunk_id TEXT;

        -- Populate chunk_id with a composite key from speech_id and chunk_index
        UPDATE speech_chunks
        SET chunk_id = speech_id || '_chunk_' || chunk_index::text
        WHERE chunk_id IS NULL;

        -- Make it NOT NULL after populating
        ALTER TABLE speech_chunks ALTER COLUMN chunk_id SET NOT NULL;

        -- Add unique constraint
        ALTER TABLE speech_chunks ADD CONSTRAINT speech_chunks_chunk_id_unique UNIQUE (chunk_id);

        RAISE NOTICE 'chunk_id column added and populated successfully';
    ELSE
        RAISE NOTICE 'chunk_id column already exists, skipping migration';
    END IF;
END $$;

-- Verify the change
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'speech_chunks'
AND column_name = 'chunk_id';
