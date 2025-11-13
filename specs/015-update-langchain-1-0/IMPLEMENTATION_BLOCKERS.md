# LangChain 1.0 Upgrade - Implementation Blockers

**Date**: 2025-10-25  
**Feature**: 014-update-langchain-1-0  
**Status**: BLOCKED - Dependency Conflict

## Blocking Issue

### Dependency Incompatibility

**Problem**: The `langchain-google-cloud-sql-pg` package (version 0.14.1 currently available) has a dependency constraint that prevents LangChain 1.0 upgrade:

```
langchain-google-cloud-sql-pg 0.14.1 requires:
- langchain-core<1.0.0,>=0.3.15
```

This directly conflicts with:
```
langchain>=1.0.0 requires:
- langchain-core>=1.0.0
```

### Evidence

1. **PyPI Metadata**: `langchain-google-cloud-sql-pg==0.14.1` (latest as of 2025-10-25) explicitly requires `langchain-core<1.0.0`

2. **GitHub Examples**: The official [langchain_quick_start.ipynb](https://github.com/googleapis/langchain-google-cloud-sql-pg-python/blob/main/samples/langchain_quick_start.ipynb) shows:
   ```python
   %pip install --upgrade --quiet langchain-google-cloud-sql-pg langchain-google-vertexai langchain
   ```
   This installs without version constraints, meaning it currently targets pre-1.0 LangChain.

3. **Local Environment**: The project's `.venv` contains:
   - `langchain-core==0.3.27` (pre-1.0)
   - `langchain-google-cloud-sql-pg==0.14.1`
   - These were installed before attempting the 1.0 upgrade.

## Resolution Path

### Option 1: Wait for Official Package Update (RECOMMENDED)

**Action**: Monitor the `langchain-google-cloud-sql-pg` package for a 1.0-compatible release.

**Timeline**: Unknown. The package maintainers (Google) need to release a version with `langchain-core>=1.0.0` support.

**Risk**: Low - ensures full compatibility and support.

**Steps**:
1. Watch https://pypi.org/project/langchain-google-cloud-sql-pg/ for new releases
2. Check release notes for LangChain 1.0 compatibility
3. Update `pyproject.toml` when available:
   ```toml
   "langchain>=1.0.0",
   "langchain-google-cloud-sql-pg>=0.15.0",  # hypothetical future version
   ```

### Option 2: Pin to Pre-1.0 LangChain (ALTERNATIVE)

**Action**: Keep LangChain at latest 0.x version and document future upgrade path.

**Timeline**: Immediate

**Risk**: Low - maintains current functionality, delays upgrade benefits.

**Steps**:
1. Update `pyproject.toml` to pin:
   ```toml
   "langchain>=0.3.0,<1.0.0",
   "langchain-text-splitters>=0.3.0,<1.0.0",
   "langchain-google-cloud-sql-pg>=0.14.0",
   ```
2. Close this feature branch as "postponed"
3. Reopen when `langchain-google-cloud-sql-pg` supports 1.0

### Option 3: Use Pre-release/Beta Versions (NOT RECOMMENDED)

**Action**: Try pre-release versions of `langchain-google-cloud-sql-pg` if available.

**Risk**: High - unstable, unsupported, may break in production.

**Not recommended for production deployment.**

## Impact Analysis

### Already Completed
- ✅ Updated `pyproject.toml` with target versions
- ✅ Refactored imports in `src/tools/` (langchain_text_splitters)
- ✅ Refactored imports in `scripts/` (all RecursiveCharacterTextSplitter uses)
- ✅ Verified `src/storage/vector_store.py` already uses 1.0-style imports

### Blocked Tasks
- ❌ T105: Install LangChain 1.0 dependencies (conflicts with cloud-sql-pg)
- ❌ T106: Run test suite (cannot install deps)
- ❌ T201-T204: Database compatibility validation (requires working install)
- ❌ T301-T303: Documentation updates (feature incomplete)

### Code Changes Are Forward-Compatible

**Important**: The import path changes we made are **forward-compatible**:
- `from langchain_text_splitters import RecursiveCharacterTextSplitter` works in both:
  - LangChain 0.3.x (via `langchain-text-splitters>=0.3.0` backport)
  - LangChain 1.0+ (native package)

This means when `langchain-google-cloud-sql-pg` releases 1.0 support, we can upgrade immediately without additional code changes.

## Recommendation

**Adopt Option 2** (Pin to Pre-1.0 with upgrade path):

1. **Immediate**: Update `pyproject.toml` to explicitly support current stack:
   ```toml
   dependencies = [
       "fastmcp>=2.14.0",
       "langchain>=0.3.0,<1.0.0",
       "langchain-text-splitters>=0.3.0",
       "langchain-google-vertexai>=2.0.0",
       "langchain-google-cloud-sql-pg>=0.14.0",
       # ... other deps
   ]
   ```

2. **Monitor**: Set up alerts for new `langchain-google-cloud-sql-pg` releases.

3. **Documentation**: Add note to README about planned LangChain 1.0 upgrade pending upstream support.

4. **Future**: When `langchain-google-cloud-sql-pg` 1.0 support releases:
   - Update version constraints
   - Run test suite (T106-T204)
   - Complete documentation (T301-T303)
   - Merge to main

## References

- LangChain 1.0 Release Notes: https://blog.langchain.dev/langchain-v0-1-0/
- LangChain Google Cloud SQL PG: https://github.com/googleapis/langchain-google-cloud-sql-pg-python
- PyPI Package: https://pypi.org/project/langchain-google-cloud-sql-pg/

## Next Steps

1. Review this analysis with team/stakeholders
2. Decide on Option 1 (wait) vs Option 2 (pin pre-1.0)
3. Update feature status in tasks.md
4. Document decision in README and plan.md
