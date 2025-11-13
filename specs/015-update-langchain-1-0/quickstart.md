# LangChain 1.0 Upgrade Quickstart

**Feature**: 014-update-langchain-1-0  
**Audience**: Developers upgrading this project to LangChain 1.0  
**Time Required**: ~2 hours (including testing)

## Overview

This guide walks you through upgrading the Hansard MCP server from LangChain 0.x to 1.0. The upgrade involves:
- Updating 2 import statements
- Adding 1 new dependency
- Validating backward compatibility

**Risk Level**: 🟢 LOW - Import changes only, no API or database changes

---

## Prerequisites

Before starting:
- [ ] You have Python 3.11+ installed
- [ ] You're on branch `014-update-langchain-1-0`
- [ ] All existing tests pass on 0.x
- [ ] Cloud SQL proxy is accessible (for database validation)

---

## Step 1: Capture Baseline (15 minutes)

**Why**: Save current behavior to verify 1.0 produces identical results

### 1.1 Save Current Dependencies

```bash
cd /home/user/skai-fastmcp-cloudrun
pip freeze > specs/014-update-langchain-1-0/pre-upgrade-deps.txt
```

### 1.2 Run Existing Tests

```bash
# Activate virtual environment
source .venv/bin/activate  # or your venv path

# Run tests and save output
PYTHONPATH=src:. python test_tools.py > specs/014-update-langchain-1-0/baseline-tests.txt 2>&1
```

**Expected**: All tests pass. Save this output for comparison.

### 1.3 Capture Sample Search Results

Start Cloud SQL proxy if not running:
```bash
./scripts/start_cloud_sql_proxy.sh
```

Query database and save results:
```python
# Create: scripts/capture_baseline.py
from src.storage.vector_store import get_vector_store

store = get_vector_store()
results = store.similarity_search("climate change", k=5)

with open("specs/014-update-langchain-1-0/baseline-search.txt", "w") as f:
    for i, doc in enumerate(results):
        f.write(f"Result {i+1}: {doc.metadata.get('speech_id', 'unknown')}\n")
        f.write(f"Content: {doc.page_content[:100]}...\n\n")
```

Run:
```bash
python scripts/capture_baseline.py
```

### 1.4 Capture Sample Chunks

```python
# Create: scripts/capture_baseline_chunks.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

sample_text = """Your 5000 character sample document here..."""

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = splitter.split_text(sample_text)

with open("specs/014-update-langchain-1-0/baseline-chunks.txt", "w") as f:
    f.write(f"Total chunks: {len(chunks)}\n\n")
    for i, chunk in enumerate(chunks):
        f.write(f"--- Chunk {i+1} ({len(chunk)} chars) ---\n")
        f.write(chunk)
        f.write("\n\n")
```

Run:
```bash
python scripts/capture_baseline_chunks.py
```

**Checkpoint**: You now have 3 baseline files to compare against after upgrade.

---

## Step 2: Update Dependencies (10 minutes)

### 2.1 Update pyproject.toml

Edit `pyproject.toml`:

```toml
# BEFORE
langchain = "*"  # or unpinned

# AFTER
langchain = ">=1.0.0"
langchain-text-splitters = ">=0.3.0"
langchain-google-vertexai = ">=2.0.0"
langchain-google-cloud-sql-pg = ">=0.14.0"
```

**Note**: If you have other version pins, adjust accordingly. The key change is adding `langchain-text-splitters`.

### 2.2 Install New Dependencies

```bash
pip install -e .
```

**Expected Output**: No dependency conflicts. If conflicts occur:
- Check for packages pinning old LangChain versions
- Update or remove conflicting packages
- Consult `research.md` compatibility matrix

### 2.3 Verify Installation

```bash
pip show langchain langchain-text-splitters
```

**Expected**:
- `langchain`: Version 1.0.0 or higher
- `langchain-text-splitters`: Version 0.3.0 or higher

---

## Step 3: Update Imports (15 minutes)

### 3.1 Update src/tools/ingest.py

**Find this line**:
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
```

**Replace with**:
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
```

**Verify**: No other LangChain imports in this file need updating.

### 3.2 Update src/tools/ingest_markdown_file.py

**Find this line**:
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
```

**Replace with**:
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
```

**Verify**: No other LangChain imports in this file need updating.

### 3.3 Verify src/storage/vector_store.py

**Check**: This file should already use new-style imports:
```python
from langchain_google_cloud_sql_pg import PostgresVectorStore, PostgresEngine
from langchain_google_vertexai import VertexAIEmbeddings
```

**Action**: ✅ No changes needed if imports match above.

---

## Step 4: Validate Compatibility (45 minutes)

### 4.1 Run Test Suite

```bash
PYTHONPATH=src:. python test_tools.py
```

**Expected**: ✅ All tests pass (identical to baseline)

**If tests fail**:
1. Check error message - is it an import issue?
2. Verify all imports updated correctly
3. Check for typos in new import paths
4. Review `research.md` for known issues

### 4.2 Compare Search Results

Rerun baseline search script:
```bash
python scripts/capture_baseline.py
```

Compare output:
```bash
diff specs/014-update-langchain-1-0/baseline-search.txt specs/014-update-langchain-1-0/baseline-search.txt
```

**Expected**: ✅ No differences (or only timestamp differences)

**If results differ**:
- Check if speech IDs match
- Verify similarity scores within 0.01 tolerance
- Investigate vector store connection issues

### 4.3 Compare Text Chunks

Rerun baseline chunks script:
```bash
python scripts/capture_baseline_chunks.py
```

Compare output:
```bash
diff specs/014-update-langchain-1-0/baseline-chunks.txt specs/014-update-langchain-1-0/baseline-chunks.txt
```

**Expected**: ✅ Byte-for-byte identical chunks

**If chunks differ**:
- This is a CRITICAL issue
- Verify `RecursiveCharacterTextSplitter` parameters unchanged
- Check if sample text was modified
- Consult LangChain 1.0 docs for undocumented changes

### 4.4 Check for Deprecation Warnings

```bash
PYTHONPATH=src:. python -W all test_tools.py 2>&1 | grep -i deprecat
```

**Expected**: ✅ No deprecation warnings

**If warnings appear**:
- Document them in upgrade notes
- Plan future remediation if needed
- Acceptable for now if not critical

### 4.5 Test MCP Server Startup

```bash
cd src
python -m mcp_server
```

**Expected**: Server starts without errors

**If errors occur**:
- Check import errors
- Verify database connection
- Review server logs for LangChain-related issues

---

## Step 5: Update Documentation (15 minutes)

### 5.1 Update Inline Comments

Review modified files for comments mentioning LangChain:

**src/tools/ingest.py**:
```python
# Update any comments like:
# OLD: "Uses langchain.text_splitter for chunking"
# NEW: "Uses langchain_text_splitters for chunking"
```

**src/tools/ingest_markdown_file.py**:
```python
# Same as above
```

### 5.2 Update Agent Context

Run the agent context update script:
```bash
.specify/scripts/bash/update-agent-context.sh copilot
```

**Manual additions** (if script doesn't auto-update):
Edit `.github/copilot-instructions.md`:

```markdown
## Active Technologies
- LangChain 1.0 with langchain-text-splitters>=0.3.0
- Python 3.11+ (Cloud Run requirement)
- PostgreSQL via Cloud SQL with pgvector extension

## Recent Changes
- 014-update-langchain-1-0: Upgraded LangChain to 1.0
  - Import path: langchain.text_splitter → langchain_text_splitters
  - All dependencies updated to 1.0-compatible versions
  - Backward compatible: existing vectors work unchanged
```

### 5.3 Update README (if applicable)

Check if `README.md` mentions LangChain:
```bash
grep -i langchain README.md
```

**If found**: Update version numbers and import examples to match 1.0.

---

## Step 6: Commit and Push (10 minutes)

### 6.1 Review Changes

```bash
git status
git diff
```

**Expected changes**:
- `pyproject.toml` - 4 dependency updates
- `src/tools/ingest.py` - 1 import line
- `src/tools/ingest_markdown_file.py` - 1 import line
- `.github/copilot-instructions.md` - Agent context update
- Any documentation updates

### 6.2 Commit Changes

```bash
git add pyproject.toml src/tools/ingest.py src/tools/ingest_markdown_file.py .github/copilot-instructions.md

git commit -m "feat(001): Upgrade LangChain to 1.0

- Update langchain to >=1.0.0
- Add langchain-text-splitters>=0.3.0 dependency
- Update RecursiveCharacterTextSplitter imports in ingest tools
- Update agent context with LangChain 1.0 patterns
- All tests pass, backward compatible with existing vectors

Validation:
- Test suite: PASS (identical to 0.x baseline)
- Search results: IDENTICAL (speech IDs match)
- Text chunks: IDENTICAL (byte-for-byte match)
- Deprecation warnings: NONE
"
```

### 6.3 Push to Remote

```bash
git push origin 014-update-langchain-1-0
```

---

## Step 7: Deploy and Validate (15 minutes)

### 7.1 Create Pull Request

**Title**: `feat(001): Upgrade LangChain to 1.0`

**Description**:
```markdown
## Summary
Upgrades LangChain from 0.x to 1.0 to enable security updates and modern features.

## Changes
- Updated 2 import statements (text splitter module path)
- Added langchain-text-splitters dependency
- All tests pass (100% backward compatible)
- Existing database vectors work unchanged

## Validation
- ✅ Test suite: All pass
- ✅ Search results: Identical to 0.x baseline
- ✅ Text chunks: Byte-for-byte match
- ✅ No deprecation warnings

## Risk Assessment
🟢 LOW RISK - Import changes only, no API or database changes

## Rollback Plan
Revert dependencies to 0.x versions if issues arise (pre-upgrade-deps.txt saved)
```

### 7.2 Deploy to Cloud Run

```bash
gcloud run deploy hansard-mcp \
  --source . \
  --region us-central1 \
  --platform managed
```

**Expected**: Deployment succeeds, health check passes

### 7.3 Validate Production

Test MCP tool calls in production:
```bash
# Use MCP inspector or Claude Desktop to test
# Verify search and ingest tools work
```

**Expected**: All tools work identically to before upgrade

---

## Troubleshooting

### Import Error: "No module named langchain_text_splitters"

**Problem**: New dependency not installed

**Solution**:
```bash
pip install langchain-text-splitters>=0.3.0
```

### Test Failures After Upgrade

**Problem**: Tests fail with LangChain 1.0

**Solution**:
1. Check error message for specific API changes
2. Verify all imports updated correctly
3. Review `research.md` for known issues
4. Consider rollback if unresolvable

### Different Search Results

**Problem**: Vector search returns different speeches

**Critical**: This indicates vector incompatibility

**Solution**:
1. Verify database connection
2. Check embedding dimensions match
3. Compare similarity scores (should be within 0.01)
4. If scores differ significantly, investigate embedding model compatibility
5. Worst case: Rollback and re-research

### Deprecation Warnings

**Problem**: Warnings appear in logs

**Solution**:
- Document warnings (not blocking)
- Plan future remediation if needed
- Monitor for breaking changes in future releases

---

## Rollback Procedure

If critical issues arise:

### 1. Revert Dependencies

```bash
pip uninstall langchain langchain-text-splitters
pip install -r specs/014-update-langchain-1-0/pre-upgrade-deps.txt
```

### 2. Revert Code Changes

```bash
git checkout main -- pyproject.toml src/tools/ingest.py src/tools/ingest_markdown_file.py
```

### 3. Verify Rollback

```bash
PYTHONPATH=src:. python test_tools.py
```

**Expected**: Tests pass with 0.x

### 4. Document Issues

Add to `specs/014-update-langchain-1-0/rollback-notes.md`:
- What failed
- Error messages
- Hypotheses for root cause
- Plan for retry

---

## Success Checklist

Before marking upgrade complete:

- [ ] All tests pass with LangChain 1.0
- [ ] Search results match 0.x baseline
- [ ] Text chunks match 0.x baseline
- [ ] No deprecation warnings
- [ ] MCP server starts successfully
- [ ] Production deployment succeeds
- [ ] MCP tools work in Claude Desktop/Inspector
- [ ] Documentation updated
- [ ] Agent context updated
- [ ] Changes committed and pushed
- [ ] Pull request created

---

## Next Steps

After successful upgrade:

1. **Monitor**: Watch for any issues in production
2. **Document**: Note any learnings or gotchas
3. **Share**: Update team on successful migration
4. **Plan**: Consider other dependency upgrades with similar low risk

---

## Resources

- [LangChain 1.0 Migration Guide](https://python.langchain.com/docs/versions/migrating/)
- [langchain-text-splitters Documentation](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [Feature Spec](./spec.md)
- [Research Findings](./research.md)
- [Implementation Plan](./plan.md)

---

**Last Updated**: 2025-10-25  
**Maintainer**: Development Team  
**Status**: Ready for implementation
