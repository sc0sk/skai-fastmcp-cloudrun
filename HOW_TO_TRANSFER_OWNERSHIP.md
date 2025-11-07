# Transfer Table Ownership from scott.coleman@aph.gov.au

## The Problem

The LangChain tables are owned by `scott.coleman@aph.gov.au`:
- `langchain_pg_collection`
- `langchain_pg_embedding`

ChatGPT is connecting as `666924716777-compute@developer` (the IAM service account) and getting "permission denied" errors because it doesn't own these tables.

## Solution: Transfer Ownership

You need to connect to the database as `scott.coleman@aph.gov.au` and transfer ownership.

### Option 1: Cloud Console (Easiest)

1. **Go to Cloud SQL Studio**
   - URL: https://console.cloud.google.com/sql/instances/hansard-db-v2/studio?project=skai-fastmcp-cloudrun
   - Or: Cloud SQL → hansard-db-v2 → Cloud SQL Studio tab

2. **Connect as scott.coleman@aph.gov.au**
   - Database: `hansard`
   - User: `scott.coleman@aph.gov.au`
   - Password: (you'll need Scott's password)

3. **Run the SQL script**
   - Copy all contents from `transfer_ownership_from_scott.sql`
   - Paste into SQL editor
   - Click **Execute**

4. **Done!** ChatGPT should now work

### Option 2: Command Line

```bash
# You'll be prompted for scott.coleman@aph.gov.au's password
gcloud sql connect hansard-db-v2 \
  --user=scott.coleman@aph.gov.au \
  --database=hansard \
  --project=skai-fastmcp-cloudrun < transfer_ownership_from_scott.sql
```

### Alternative: Grant Permissions Instead

If you can't access Scott's account, you could also just grant permissions:

**Run this as scott.coleman@aph.gov.au:**

```sql
GRANT ALL PRIVILEGES ON langchain_pg_collection TO "666924716777-compute@developer";
GRANT ALL PRIVILEGES ON langchain_pg_embedding TO "666924716777-compute@developer";
```

This would work too, but transferring ownership is cleaner since the IAM user should own the tables it manages.

---

## After Running

1. Go back to ChatGPT
2. Try: "Search Hansard for speeches about housing"
3. Should work! ✅

The error will change from:
```
❌ permission denied for table langchain_pg_collection
```

To:
```
✅ [search results shown]
```
