# Grant Cloud Run Service Account Database Permissions

## The Problem

The IAM user `666924716777-compute@developer` owns the tables but is getting "permission denied" errors. This is because:
1. The service account created the tables when it first connected
2. But it doesn't have the `cloudsqlsuperuser` role to manage permissions
3. We need to grant it proper database roles through Cloud IAM

## Solution: Use gcloud CLI (Fastest)

Run these commands to grant the necessary roles:

```bash
# Grant Cloud SQL Client role (to connect)
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
  --member="serviceAccount:666924716777-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Grant Cloud SQL Instance User role (for IAM authentication)
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
  --member="serviceAccount:666924716777-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.instanceUser"
```

## Alternative: Transfer Table Ownership to postgres

If the tables are owned by the IAM user, we need to run this **as the IAM user** (through the Cloud Run application):

```sql
-- Run this through the Cloud Run app (create a debug endpoint)
ALTER TABLE langchain_pg_collection OWNER TO postgres;
ALTER TABLE langchain_pg_embedding OWNER TO postgres;
ALTER TABLE hansard_speeches OWNER TO postgres;

-- Then as postgres, grant back to IAM user
GRANT ALL PRIVILEGES ON langchain_pg_collection TO "666924716777-compute@developer";
GRANT ALL PRIVILEGES ON langchain_pg_embedding TO "666924716777-compute@developer";
GRANT ALL PRIVILEGES ON hansard_speeches TO "666924716777-compute@developer";
```

## Best Solution: Grant postgres Superuser Temporarily

Run this to make postgres a superuser, fix permissions, then remove superuser:

```sql
-- In Cloud Console as cloudsqladmin or root
ALTER USER postgres WITH SUPERUSER;

-- Now run fix_langchain_permissions.sql as postgres

-- After fixing, remove superuser (security best practice)
ALTER USER postgres WITH NOSUPERUSER;
```

## Check Current IAM Roles

```bash
gcloud projects get-iam-policy skai-fastmcp-cloudrun \
  --flatten="bindings[].members" \
  --filter="bindings.members:666924716777-compute@developer.gserviceaccount.com" \
  --format="table(bindings.role)"
```
