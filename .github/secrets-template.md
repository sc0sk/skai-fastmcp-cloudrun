# GitHub Secrets Configuration

This document provides instructions for configuring GitHub secrets and variables for the Australian Hansard RAG project.

## Project Information

- **GCP Project ID**: `skai-fastmcp-cloudrun`
- **GCP Project Number**: `666924716777`
- **Default Region**: `us-central1`

## Repository Variables (Public, Non-Sensitive)

These are already configured via `gh variable set`:

| Variable | Value | Description |
|----------|-------|-------------|
| `GCP_PROJECT_ID` | `skai-fastmcp-cloudrun` | Google Cloud Project ID |
| `GCP_PROJECT_NUMBER` | `666924716777` | Google Cloud Project Number |
| `GCP_REGION` | `us-central1` | Default deployment region |

## Repository Secrets (Sensitive Data)

### Required Secrets for CI/CD

#### 1. GCP_SERVICE_ACCOUNT_KEY

**Service Account Setup**:

```bash
# Set project
export PROJECT_ID="skai-fastmcp-cloudrun"
gcloud config set project $PROJECT_ID

# Create service account for GitHub Actions
gcloud iam service-accounts create github-actions-sa \
    --display-name="GitHub Actions Service Account" \
    --description="Service account for CI/CD deployments"

# Get service account email
export SA_EMAIL="github-actions-sa@skai-fastmcp-cloudrun.iam.gserviceaccount.com"

# Grant required IAM roles
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.admin"

# Create and download JSON key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account="${SA_EMAIL}"

# Base64 encode the key for GitHub secret
cat github-actions-key.json | base64 > github-actions-key-base64.txt

# Set as GitHub secret
gh secret set GCP_SERVICE_ACCOUNT_KEY < github-actions-key-base64.txt

# IMPORTANT: Delete local key files after upload
rm github-actions-key.json github-actions-key-base64.txt
```

**Required IAM Roles**:
- `roles/run.admin` - Deploy to Cloud Run
- `roles/cloudsql.client` - Connect to Cloud SQL
- `roles/aiplatform.user` - Access Vertex AI embeddings
- `roles/iam.serviceAccountUser` - Impersonate service accounts
- `roles/storage.admin` - Access Cloud Storage (for build artifacts)

#### 2. CLOUDSQL_INSTANCE

**Cloud SQL Instance Name**:

```bash
# Set Cloud SQL instance name (format: project:region:instance)
gh secret set CLOUDSQL_INSTANCE --body "skai-fastmcp-cloudrun:us-central1:hansard-db"
```

#### 3. DATABASE_PASSWORD (Optional for MVP)

**Database Password** (if using password authentication):

```bash
# Generate secure password
export DB_PASSWORD=$(openssl rand -base64 32)

# Set as GitHub secret
gh secret set DATABASE_PASSWORD --body "$DB_PASSWORD"

# Also set in Cloud SQL
gcloud sql users set-password postgres \
    --instance=hansard-db \
    --password="$DB_PASSWORD"
```

**Note**: For production, use Cloud SQL IAM authentication instead of passwords.

## Environment-Specific Secrets (Future)

### Staging Environment

```bash
gh secret set STAGING_GCP_PROJECT_ID --body "skai-fastmcp-cloudrun-staging"
gh secret set STAGING_CLOUDSQL_INSTANCE --body "skai-fastmcp-cloudrun-staging:us-central1:hansard-db-staging"
```

### Production Environment

```bash
gh secret set PROD_GCP_PROJECT_ID --body "skai-fastmcp-cloudrun-prod"
gh secret set PROD_CLOUDSQL_INSTANCE --body "skai-fastmcp-cloudrun-prod:us-central1:hansard-db-prod"
```

## Verification

### Check Variables

```bash
gh variable list
```

Expected output:
```
GCP_PROJECT_ID       skai-fastmcp-cloudrun    2025-10-21T01:57:56Z
GCP_PROJECT_NUMBER   666924716777             2025-10-21T01:58:00Z
GCP_REGION           us-central1              2025-10-21T01:58:03Z
```

### Check Secrets

```bash
gh secret list
```

Expected output:
```
GCP_SERVICE_ACCOUNT_KEY    Updated 2025-10-21
CLOUDSQL_INSTANCE          Updated 2025-10-21
DATABASE_PASSWORD          Updated 2025-10-21 (optional)
```

### Test Service Account Permissions

```bash
# Authenticate with service account key
gcloud auth activate-service-account --key-file=github-actions-key.json

# Test Cloud Run access
gcloud run services list --project=skai-fastmcp-cloudrun --region=us-central1

# Test Vertex AI access
gcloud ai models list --project=skai-fastmcp-cloudrun --region=us-central1

# Test Cloud SQL access
gcloud sql instances describe hansard-db --project=skai-fastmcp-cloudrun
```

## Security Best Practices

### ✅ Do

1. **Use IAM Service Accounts** - Never use personal credentials
2. **Principle of Least Privilege** - Grant only required roles
3. **Rotate Keys Regularly** - Set up 90-day rotation schedule
4. **Use Secret Scanning** - Enable GitHub secret scanning
5. **Environment Separation** - Use different service accounts for staging/prod
6. **Audit Logs** - Monitor service account usage in Cloud Console

### ❌ Don't

1. **Never commit credentials** - Use .gitignore for *-key.json files
2. **Never share keys** - Each environment gets its own service account
3. **Never use owner/editor roles** - Too permissive
4. **Never log secrets** - Mask secrets in CI/CD logs
5. **Never store keys in repository** - Use GitHub Secrets only

## Cloud SQL IAM Authentication (Recommended for Production)

Instead of password authentication, use Cloud SQL IAM authentication:

```bash
# Grant Cloud SQL Client role to service account
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"

# Grant IAM database user role
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.instanceUser"

# Create IAM database user
gcloud sql users create ${SA_EMAIL} \
    --instance=hansard-db \
    --type=CLOUD_IAM_SERVICE_ACCOUNT
```

**Connection String** (with IAM):
```python
# In application code
connection_string = f"postgresql://{SA_EMAIL}@/{database}?host=/cloudsql/{instance_connection_name}"
```

## Workload Identity Federation (Advanced - Future)

For keyless authentication without service account keys:

```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create github-actions-pool \
    --project=skai-fastmcp-cloudrun \
    --location=global \
    --display-name="GitHub Actions Pool"

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc github-actions-provider \
    --project=skai-fastmcp-cloudrun \
    --location=global \
    --workload-identity-pool=github-actions-pool \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"

# Grant permissions
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="principalSet://iam.googleapis.com/projects/666924716777/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/sc0sk/skai-fastmcp-cloudrun" \
    --role="roles/run.admin"
```

**GitHub Actions Workflow** (with Workload Identity):
```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/666924716777/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider'
    service_account: 'github-actions-sa@skai-fastmcp-cloudrun.iam.gserviceaccount.com'
```

## Support

For issues with secrets or permissions:
1. Check [Cloud IAM documentation](https://cloud.google.com/iam/docs)
2. Review [GitHub Secrets documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
3. Create issue in repository with error details

---

**Last Updated**: 2025-10-21
**Project**: skai-fastmcp-cloudrun (666924716777)
**Maintainer**: sc0sk
