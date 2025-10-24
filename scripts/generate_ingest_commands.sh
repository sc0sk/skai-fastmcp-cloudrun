#!/bin/bash
# Generate Claude CLI commands for bulk markdown ingestion
#
# This script creates commands that can be run via Claude Code CLI
# to ingest all converted Hansard markdown files.

INPUT_DIR="/home/user/skai-fastmcp-cloudrun/data/hansard_converted"
OUTPUT_FILE="/home/user/skai-fastmcp-cloudrun/data/ingest_commands.txt"

echo "Generating Claude CLI ingestion commands..."
echo "Input directory: $INPUT_DIR"
echo "Output file: $OUTPUT_FILE"
echo

# Count files
FILE_COUNT=$(find "$INPUT_DIR" -name "*.md" | wc -l)
echo "Found $FILE_COUNT markdown files"
echo

# Generate commands
echo "# Claude Code CLI Commands for Bulk Hansard Ingestion" > "$OUTPUT_FILE"
echo "# Generated: $(date)" >> "$OUTPUT_FILE"
echo "# Files: $FILE_COUNT" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

find "$INPUT_DIR" -name "*.md" | sort | while read -r filepath; do
    filename=$(basename "$filepath")
    echo "claude \"ingest the markdown file at $filepath\"" >> "$OUTPUT_FILE"
done

echo "✅ Generated $FILE_COUNT ingestion commands"
echo "Output saved to: $OUTPUT_FILE"
echo
echo "To ingest all files, run:"
echo "  bash $OUTPUT_FILE"
echo
echo "Or ingest one at a time:"
echo "  head -5 $OUTPUT_FILE"
