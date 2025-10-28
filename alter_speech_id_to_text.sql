-- Alter speech_id column from UUID to TEXT to match ingestion format
-- This fixes the schema mismatch where vector embeddings use TEXT identifiers

ALTER TABLE speeches ALTER COLUMN speech_id TYPE TEXT;

-- Verify the change
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'speeches' 
AND column_name = 'speech_id';
