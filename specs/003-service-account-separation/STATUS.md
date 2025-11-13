# Feature 003 Status: Service Account Separation

**Created**: 2025-10-23
**Status**: ⚠️ **PARTIALLY IMPLEMENTED** (not deployed)
**Updated**: 2025-11-14

## Current State

### Service Accounts Created ✅
The required service accounts have been created in GCP:

```bash
hansard-db-admin@skai-fastmcp-cloudrun.iam.gserviceaccount.com       # Read-write (ingestion)
hansard-db-readonly@skai-fastmcp-cloudrun.iam.gserviceaccount.com    # Read-only (MCP server)
```

### Configuration Ready ✅
Service account constants defined in `src/config.py`:
- `DB_ADMIN_SERVICE_ACCOUNT` = `hansard-db-admin@skai-fastmcp-cloudrun.iam`
- `DB_READONLY_SERVICE_ACCOUNT` = `hansard-db-readonly@skai-fastmcp-cloudrun.iam`

### NOT Deployed ❌
The MCP server Cloud Run service still uses the **default compute service account**:
```
666924716777-compute@developer.gserviceaccount.com
```

## What's Missing

To complete this feature:

1. **Update Cloud Run deployment** to use read-only service account:
   ```bash
   gcloud run services update hansard-mcp-server \
     --service-account=hansard-db-readonly@skai-fastmcp-cloudrun.iam.gserviceaccount.com \
     --region=us-central1
   ```

2. **Update ingestion jobs** to use read-write service account (if separate jobs exist)

3. **Verify database permissions**:
   - `hansard-db-readonly@` has SELECT only on hansard database
   - `hansard-db-admin@` has CREATE/INSERT/UPDATE/DELETE

4. **Test** that search/fetch tools work with read-only account

## Decision Needed

**Option 1: Complete the implementation**
- Deploy Cloud Run with read-only service account
- Verify permissions are correctly configured
- Add `plan.md` and `tasks.md` to spec
- Mark feature as complete

**Option 2: Defer/deprecate**
- Current IAM authentication works securely
- Service account separation is a "defense in depth" improvement
- Mark spec as "DEFERRED" for future security hardening

**Recommendation**: **DEFER**
- Current setup already uses IAM auth (no passwords)
- Default compute account has minimal permissions via IAM roles
- This is a nice-to-have security improvement, not critical
- Focus on features that deliver user value first

## References

- **Spec**: [spec.md](spec.md)
- **Config**: [src/config.py:17-20](../../src/config.py#L17-L20)
- **Current Service Account**: Default Compute (666924716777-compute)
