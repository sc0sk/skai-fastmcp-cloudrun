# GitHub Access Control Update

## Changes Made

Added email allowlist for GitHub OAuth authentication.

### Date
2025-11-07

### Allowed Accounts

**Email Allowlist** (via Secret Manager):
- `joseph.leese@aph.gov.au` ✅
- `scott.coleman@aph.gov.au` ✅

**Username Allowlist** (existing):
- `sc0sk` ✅

### Secret Manager Configuration

1. **Created Secret**: `github-allowed-emails`
   - Version 2 (latest): `joseph.leese@aph.gov.au,scott.coleman@aph.gov.au`
   - Location: `projects/skai-fastmcp-cloudrun/secrets/github-allowed-emails`

2. **Existing Secret**: `github-allowed-usernames`
   - Value: `sc0sk`
   - Location: `projects/skai-fastmcp-cloudrun/secrets/github-allowed-usernames`

### Cloud Run Configuration

**Environment Variable**: `GITHUB_ALLOWED_EMAILS`
- Source: Secret Manager `github-allowed-emails:latest`
- Service Account: `666924716777-compute@developer.gserviceaccount.com`
- IAM Role: `roles/secretmanager.secretAccessor`

**Service**: `hansard-mcp-server`
- Region: `us-central1`
- Project: `skai-fastmcp-cloudrun`
- Status: ✅ Ready (deployed 2025-11-07 01:34:28 UTC)

### Access Control Logic

From [src/auth/github_access_control.py](src/auth/github_access_control.py):

```python
def is_user_allowed(github_username: Optional[str], email: Optional[str] = None) -> bool:
    allowed_usernames = get_allowed_github_usernames()  # ["sc0sk"]
    allowed_emails = get_allowed_emails()  # ["joseph.leese@aph.gov.au", "scott.coleman@aph.gov.au"]

    # Check username allowlist
    if github_username and github_username in allowed_usernames:
        return True  # sc0sk allowed

    # Check email allowlist
    if email and allowed_emails and email in allowed_emails:
        return True  # joseph.leese@aph.gov.au or scott.coleman@aph.gov.au allowed

    return False  # All other users denied
```

### ⚠️ Important Note: Middleware Currently Disabled

**The access control middleware is currently DISABLED** due to a compatibility issue with FastMCP.

From [src/server.py:122-126](src/server.py#L122-L126):
```python
# TEMPORARILY DISABLED: BaseHTTPMiddleware incompatibility with FastMCP
# if auth_provider and not os.getenv("DANGEROUSLY_OMIT_AUTH", "false").lower() == "true":
#     from src.auth.github_middleware import GitHubAccessControlMiddleware
#     mcp.add_middleware(GitHubAccessControlMiddleware)
#     print("✅ GitHub access control middleware enabled")
print("⚠️  GitHub access control middleware temporarily disabled (compatibility issue)")
```

**Current Behavior**:
- ✅ OAuth authentication **IS REQUIRED** (must login with GitHub)
- ❌ Username/email restrictions **NOT ENFORCED**
- 🔓 **ANY GitHub user** can currently access the server

**Intended Behavior** (when middleware re-enabled):
- ✅ OAuth authentication required
- ✅ Only `sc0sk` username allowed
- ✅ Only `joseph.leese@aph.gov.au` and `scott.coleman@aph.gov.au` emails allowed
- ❌ All other users get 403 Forbidden

### To Enable Access Control

1. **Fix middleware compatibility** with FastMCP
2. **Uncomment lines 122-125** in `src/server.py`
3. **Redeploy** to Cloud Run:
   ```bash
   gcloud run deploy hansard-mcp-server \
     --source . \
     --region=us-central1 \
     --project=skai-fastmcp-cloudrun
   ```

### Commands Used

```bash
# Create email allowlist secret
echo "joseph.leese@aph.gov.au,scott.coleman@aph.gov.au" | \
  gcloud secrets create github-allowed-emails \
  --data-file=- \
  --project=skai-fastmcp-cloudrun \
  --replication-policy=automatic

# Grant service account access
gcloud secrets add-iam-policy-binding github-allowed-emails \
  --project=skai-fastmcp-cloudrun \
  --member="serviceAccount:666924716777-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Update Cloud Run service
gcloud run services update hansard-mcp-server \
  --region=us-central1 \
  --project=skai-fastmcp-cloudrun \
  --update-secrets=GITHUB_ALLOWED_EMAILS=github-allowed-emails:latest

# Verify configuration
gcloud secrets versions access latest --secret="github-allowed-emails" \
  --project=skai-fastmcp-cloudrun
```

### Verification

```bash
# Check secret value
$ gcloud secrets versions access latest --secret="github-allowed-emails" --project=skai-fastmcp-cloudrun
joseph.leese@aph.gov.au,scott.coleman@aph.gov.au

# Check Cloud Run env vars
$ gcloud run services describe hansard-mcp-server \
  --region=us-central1 \
  --project=skai-fastmcp-cloudrun \
  --format="get(spec.template.spec.containers[0].env)" | grep GITHUB_ALLOWED
{'name': 'GITHUB_ALLOWED_EMAILS', 'valueFrom': {'secretKeyRef': {'key': 'latest', 'name': 'github-allowed-emails'}}}
```

### Security Notes

1. **Secrets stored in Secret Manager**: Emails and usernames stored securely, not in code
2. **Service Account access**: Only compute SA can read secrets
3. **IAM permissions**: Restricted via `roles/secretmanager.secretAccessor`
4. **OAuth required**: All users must authenticate with GitHub first
5. **HTTPS only**: All traffic encrypted in transit

### Next Steps

To fully activate access control:

1. [ ] Fix `BaseHTTPMiddleware` compatibility with FastMCP
2. [ ] Re-enable middleware in `src/server.py`
3. [ ] Test with allowed users (joseph.leese@aph.gov.au, scott.coleman@aph.gov.au, sc0sk)
4. [ ] Test with unauthorized user (should get 403)
5. [ ] Deploy to production

### Related Files

- [src/auth/github_access_control.py](src/auth/github_access_control.py) - Access control logic
- [src/auth/github_middleware.py](src/auth/github_middleware.py) - Starlette middleware (disabled)
- [src/server.py](src/server.py) - Server configuration

### Git History

- `c341679` - Add GitHub username and email access control
- `57bca76` - Fix: update fetch tool to use client-side filtering and allow wildcard GitHub auth
- `9631128` - Docs: add production deployment guide and whitelist secret documentation
- `d463fe8` - Feat: add GitHub username whitelist authorization (sc0sk only)
