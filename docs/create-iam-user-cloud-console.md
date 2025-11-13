# Create IAM Database User via Google Cloud Console

This guide shows how to create the IAM database user `666924716777-compute@developer` using the Google Cloud Console web interface.

## Option 1: Cloud Shell SQL Editor (Easiest)

### Step 1: Open Cloud SQL Instance
1. Go to: https://console.cloud.google.com/sql/instances/hansard-db-v2?project=skai-fastmcp-cloudrun
2. Click on **"hansard-db-v2"** instance name

### Step 2: Open Cloud Shell Editor
1. Click the **"OPEN CLOUD SHELL EDITOR"** button (top right)
   - OR click the **"Connect to this instance"** dropdown
   - Select **"Open Cloud Shell"**

### Step 3: Connect to Database
In Cloud Shell, run:

```bash
# Get the postgres password
gcloud secrets versions access latest --secret=CLOUDSQL_PASSWORD

# Connect to the database
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard

# When prompted, paste the password from above
```

### Step 4: Create IAM User
Once connected to `psql`, run these commands:

```sql
-- Create the IAM user
CREATE USER "666924716777-compute@developer" WITH LOGIN;

-- Grant database access
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";

-- Grant schema access
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
TO "666924716777-compute@developer";

-- Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public
TO "666924716777-compute@developer";

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
TO "666924716777-compute@developer";

-- Set default privileges for future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES
TO "666924716777-compute@developer";
```

### Step 5: Verify User Creation

```sql
-- Check user exists
SELECT rolname FROM pg_roles WHERE rolname = '666924716777-compute@developer';

-- Should return:
--             rolname
-- ----------------------------------
--  666924716777-compute@developer
-- (1 row)

-- Check permissions
SELECT table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = '666924716777-compute@developer'
ORDER BY table_name, privilege_type;

-- Should show SELECT, INSERT, UPDATE, DELETE for all tables
```

### Step 6: Exit and Test

```sql
\q  -- Exit psql
```

Now test ChatGPT search - it should work!

---

## Option 2: Using Automated Script (Faster)

If you have the `create_iam_db_user.sql` file:

```bash
# 1. Get password
gcloud secrets versions access latest --secret=CLOUDSQL_PASSWORD

# 2. Connect
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard

# 3. Run the script
\i create_iam_db_user.sql
```

---

## Option 3: Cloud Console SQL Editor (Web UI)

### Step 1: Navigate to Cloud SQL
1. Go to: https://console.cloud.google.com/sql/instances/hansard-db-v2?project=skai-fastmcp-cloudrun

### Step 2: Open SQL Workspace
1. Click **"SQL Workspace"** in the left sidebar
   - OR click **"Overview"** → **"Open SQL Workspace"**

### Step 3: Authenticate
1. Select database: **hansard**
2. Select user: **postgres**
3. Click **"Authenticate"**
4. Get password: Run in Cloud Shell:
   ```bash
   gcloud secrets versions access latest --secret=CLOUDSQL_PASSWORD
   ```
5. Paste the password and click **"OK"**

### Step 4: Run SQL Commands
In the SQL editor, paste and run:

```sql
-- Create IAM user
CREATE USER "666924716777-compute@developer" WITH LOGIN;

-- Grant all permissions
GRANT CONNECT ON DATABASE hansard TO "666924716777-compute@developer";
GRANT USAGE ON SCHEMA public TO "666924716777-compute@developer";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "666924716777-compute@developer";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "666924716777-compute@developer";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "666924716777-compute@developer";

-- Verify
SELECT rolname FROM pg_roles WHERE rolname = '666924716777-compute@developer';
```

Click **"Run"** or press **Ctrl+Enter**

---

## Troubleshooting

### Error: "role already exists"
✅ Good! The user already exists. Just run the GRANT statements.

### Error: "permission denied"
Make sure you're connected as the **postgres** superuser, not another user.

### Error: "database does not exist"
Make sure you selected database **hansard** (not postgres or another database).

### How to verify it worked?
After creating the user, test ChatGPT search:
1. Go to your ChatGPT GPT
2. Try a search query
3. Check Cloud Run logs:
   ```bash
   gcloud logging read 'resource.labels.service_name=hansard-mcp-server AND textPayload=~"Stripped.*suffix"' --limit 5
   ```
4. Should see: "Stripped .gserviceaccount.com suffix for database username"

---

## Why This Format?

The user must be named **exactly** `666924716777-compute@developer` (with quotes, without the `.gserviceaccount.com` suffix) because:

1. **Cloud Run's metadata server returns**: `666924716777-compute@developer.gserviceaccount.com`
2. **Our code strips the suffix**: `.gserviceaccount.com` → `666924716777-compute@developer`
3. **Cloud SQL IAM expects**: The shortened format (without suffix) as the database username

This is the standard format for Cloud SQL IAM authentication with Compute Engine service accounts.

---

## Next Steps

After creating the user:
1. ✅ Test ChatGPT search
2. ✅ Verify in logs that IAM authentication is working
3. ✅ Merge code changes to main (Feature 019 + OAuth fixes)

The code is ready and deployed (revision 00112-7z5), just needs the database user to exist!
