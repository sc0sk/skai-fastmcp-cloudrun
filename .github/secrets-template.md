# GitHub Secrets Configuration

This document lists the GitHub secrets required for CI/CD and deployment.

## Required Secrets

### Google Cloud Platform Credentials

These secrets are needed for Cloud Run deployment and Vertex AI access.

#### 1. GCP_PROJECT_ID
**Description**: Your Google Cloud Project ID
**Type**: Repository secret
**Example**: `my-project-123456`

```bash
# Set via GitHub CLI
gh secret set GCP_PROJECT_ID --body "your-project-id"

# Or via GitHub UI: Settings → Secrets and variables → Actions → New repository secret
```

#### 2. GCP_SERVICE_ACCOUNT_KEY
**Description**: Service account JSON key with required permissions
**Type**: Repository secret
**Format**: Base64-encoded JSON key

**Required IAM Roles**:
- Cloud Run Admin (`roles/run.admin`)
- Cloud SQL Client (`roles/cloudsql.client`)
- Vertex AI User (`roles/aiplatform.user`)
- Secret Manager Secret Accessor (`roles/secretmanager.secretAccessor`)
- Service Account User (`roles/iam.serviceAccountUser`)

**How to create**:
```bash
# 1. Create service account
gcloud iam service-accounts create github-actions-deployer \
    --display-name="GitHub Actions Deployer" \
    --description="Service account for GitHub Actions CI/CD"

# 2. Grant required roles
PROJECT_ID="your-project-id"
SA_EMAIL="github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

for role in \
    "roles/run.admin" \
    "roles/cloudsql.client" \
    "roles/aiplatform.user" \
    "roles/secretmanager.secretAccessor" \
    "roles/iam.serviceAccountUser"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role"
done

# 3. Create and download key
gcloud iam service-accounts keys create ~/gcp-key.json \
    --iam-account="${SA_EMAIL}"

# 4. Set as GitHub secret (base64 encoded)
gh secret set GCP_SERVICE_ACCOUNT_KEY < ~/gcp-key.json

# 5. Delete local key file (security)
rm ~/gcp-key.json
```

#### 3. GCP_REGION
**Description**: Google Cloud region for deployment
**Type**: Repository secret or variable
**Default**: `us-central1`

```bash
gh secret set GCP_REGION --body "us-central1"
# Or as variable (not secret):
gh variable set GCP_REGION --body "us-central1"
```

#### 4. CLOUDSQL_INSTANCE
**Description**: Cloud SQL instance name
**Type**: Repository secret or variable
**Example**: `hansard-db`

```bash
gh secret set CLOUDSQL_INSTANCE --body "hansard-db"
```

### GitHub OAuth (Deferred to v2)

These secrets will be needed when implementing GitHub OAuth authentication.

#### 5. GITHUB_CLIENT_ID (v2 only)
**Description**: GitHub OAuth App Client ID
**Type**: Repository secret

```bash
gh secret set GITHUB_CLIENT_ID --body "your-oauth-client-id"
```

#### 6. GITHUB_CLIENT_SECRET (v2 only)
**Description**: GitHub OAuth App Client Secret
**Type**: Repository secret

```bash
gh secret set GITHUB_CLIENT_SECRET --body "your-oauth-client-secret"
```

---

## Repository Variables (Non-Sensitive)

These can be set as repository variables instead of secrets.

```bash
# Python version
gh variable set PYTHON_VERSION --body "3.11"

# FastMCP version
gh variable set FASTMCP_VERSION --body "2.14.0"

# Cloud Run service name
gh variable set CLOUD_RUN_SERVICE --body "hansard-mcp-server"
```

---

## Verification

After setting secrets, verify they're configured:

```bash
# List all secrets (values are hidden)
gh secret list

# List all variables
gh variable list
```

---

## Environment-Specific Secrets

For staging vs production environments:

```bash
# Create environments in GitHub
gh api repos/sc0sk/skai-fastmcp-cloudrun/environments/staging --method PUT
gh api repos/sc0sk/skai-fastmcp-cloudrun/environments/production --method PUT

# Set environment-specific secrets
gh secret set GCP_PROJECT_ID --env staging --body "project-staging"
gh secret set GCP_PROJECT_ID --env production --body "project-production"
```

---

## Security Best Practices

1. ✅ **Rotate secrets regularly** (every 90 days)
2. ✅ **Use separate service accounts** for staging and production
3. ✅ **Minimize IAM permissions** (principle of least privilege)
4. ✅ **Never commit secrets** to version control
5. ✅ **Delete downloaded key files** after uploading to GitHub
6. ✅ **Use environment protection rules** for production
7. ✅ **Enable secret scanning** in repository settings

---

## Local Development

For local development, use `.env` file (already gitignored):

```bash
# Copy template
cp .env.example .env

# Edit with your values
# .env is automatically ignored by git
```

**Never use GitHub secrets values locally** - they're for CI/CD only.

---

## Next Steps

1. [ ] Set up GCP_PROJECT_ID secret
2. [ ] Create service account and set GCP_SERVICE_ACCOUNT_KEY
3. [ ] Set GCP_REGION and CLOUDSQL_INSTANCE
4. [ ] Verify secrets with `gh secret list`
5. [ ] Test deployment workflow

**Status**: ⏳ Secrets not yet configured
**Required for**: Cloud Run deployment, Vertex AI access, CI/CD pipelines
