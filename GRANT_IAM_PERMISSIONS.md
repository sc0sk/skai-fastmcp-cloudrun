# Grant IAM Database Permissions

## Summary

IAM user `666924716777-compute@developer` has been created in Cloud SQL successfully. Now database-level permissions need to be granted through the Cloud Console SQL Editor.

## What Was Done

1. ✅ Created IAM database user: `666924716777-compute@developer`  
   ```bash
   gcloud sql users create "666924716777-compute@developer" --instance=hansard-db-v2 --type=CLOUD_IAM_SERVICE_ACCOUNT --project=skai-fastmcp-cloudrun
   ```

2. ✅ Cloud Run service account already has Cloud SQL Client role (`roles/cloudsql.client`)

## What You Need to Do

Execute the SQL commands in `grant_iam_db_permissions.sql` via Cloud Console:

1. Go to Cloud SQL Console: https://console.cloud.google.com/sql/instances/hansard-db-v2/overview?project=skai-fastmcp-cloudrun
2. Click "Open Cloud Shell Editor" or use the SQL editor
3. Connect to database "hansard"
4. Run these commands:

```sql
-- Grant USAGE on schema
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";

-- Grant SELECT, INSERT, UPDATE on hansard_speeches table
GRANT SELECT, INSERT, UPDATE ON TABLE hansard_speeches TO "666924716777-compute@developer";

-- Grant USAGE on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";

-- Change table owner (allows LangChain to manage the table)
ALTER TABLE hansard_speeches OWNER TO "666924716777-compute@developer";
```

## Verification

After running the SQL commands, test the IAM connection:

```bash
PYTHONPATH=src GCP_PROJECT_ID=skai-fastmcp-cloudrun GCP_REGION=us-central1 CLOUDSQL_INSTANCE=hansard-db-v2 CLOUDSQL_DATABASE=hansard uv run python3 scripts/init_langchain_schema.py
```

This should connect successfully using IAM authentication (no password needed).

## Next Steps

Once IAM permissions are verified:

1. Populate database with Hansard speeches:
   ```bash
   PYTHONPATH=src GCP_PROJECT_ID=skai-fastmcp-cloudrun GCP_REGION=us-central1 CLOUDSQL_INSTANCE=hansard-db-v2 CLOUDSQL_DATABASE=hansard uv run python3 scripts/populate_hansard_speeches.py
   ```

2. Test search functionality via MCP Inspector

## Troubleshooting

- If you see "password authentication failed", IAM permissions are not set up correctly
- Ensure you're connected to the "hansard" database (not "postgres")
- The IAM user format must be `service-account-name@developer` (without `.gserviceaccount.com`)
