# Fix LangChain Table Permissions

## Quick Steps (Google Cloud Console)

1. **Open Cloud SQL Studio**
   - Go to: https://console.cloud.google.com/sql/instances/hansard-db-v2/studio?project=skai-fastmcp-cloudrun
   - Or navigate to: Cloud SQL → hansard-db-v2 → Cloud SQL Studio tab

2. **Connect to database**
   - Database: `hansard`
   - User: `postgres`
   - Password: (from Secret Manager or the password we just set: `efzDDQ1Mxb8VOOAUzJsEVsKdJxtBXTdF`)

3. **Run the SQL script**
   - Copy all contents from `fix_langchain_permissions.sql`
   - Paste into the SQL editor
   - Click **Execute** or press `Ctrl+Enter`

4. **Verify**
   - You should see a table showing permissions granted:
     ```
     grantee                              | table_name              | privilege_type
     -------------------------------------+------------------------+---------------
     666924716777-compute@developer       | langchain_pg_collection| DELETE
     666924716777-compute@developer       | langchain_pg_collection| INSERT
     666924716777-compute@developer       | langchain_pg_collection| SELECT
     666924716777-compute@developer       | langchain_pg_collection| UPDATE
     ...
     ```

5. **Test ChatGPT**
   - Go back to ChatGPT
   - Try a search query: "Search for speeches about housing"
   - Should work now! ✅

---

## Alternative: Command Line

If you prefer command line:

```bash
# Get the postgres password from Secret Manager
gcloud secrets versions access latest --secret=CLOUDSQL_PASSWORD

# Connect and run the script
gcloud sql connect hansard-db-v2 \
  --user=postgres \
  --database=hansard \
  --project=skai-fastmcp-cloudrun < fix_langchain_permissions.sql
```

---

## What This Fixes

ChatGPT was getting this error:
```
permission denied for table langchain_pg_collection
```

The IAM user (`666924716777-compute@developer`) needs access to:
- `langchain_pg_collection` - LangChain vector store metadata
- `langchain_pg_embedding` - LangChain vector embeddings
- `hansard_speeches` - Our custom speech metadata

This script grants all necessary permissions.
