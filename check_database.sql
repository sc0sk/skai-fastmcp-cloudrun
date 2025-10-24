-- Run this in Cloud Console SQL Editor to check if database has been populated

-- Count total records
SELECT COUNT(*) as total_records FROM hansard_speeches;

-- Show sample records if any exist
SELECT speaker, date, LEFT(content, 100) as content_preview 
FROM hansard_speeches 
LIMIT 5;

-- Show table structure
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'hansard_speeches'
ORDER BY ordinal_position;
