# Data Migration Explained - Simple Guide

## What is the Data Migration?

Think of it like moving your belongings from an old house to a new house. Your Hansard speech data currently lives in an **old table** (`hansard_speeches`), and we need to copy it to a **new table structure** (`langchain_pg_embedding`) so the new code can use it.

---

## Current Situation

```
📊 Your Database Right Now:

┌─────────────────────────────┐
│  hansard_speeches (OLD)     │  ← Used by legacy code
│  ├─ ~10,000+ speech records │
│  ├─ Embeddings (vectors)    │
│  └─ Metadata (dates, etc)   │
└─────────────────────────────┘

┌─────────────────────────────┐
│  langchain_pg_embedding(NEW)│  ← Used by new code
│  └─ EMPTY (not migrated yet)│
└─────────────────────────────┘
```

---

## What the Migration Does

The migration script **copies** data from the old table to the new table:

1. **Reads** 100 records at a time from `hansard_speeches` (old)
2. **Transforms** them to the new format
3. **Inserts** them into `langchain_pg_embedding` (new)
4. **Validates** everything copied correctly

### Important Points:

✅ **Safe**: It's a COPY, not a MOVE - your old data stays intact  
✅ **Idempotent**: Can run multiple times safely (skips duplicates)  
✅ **Fast**: Takes ~5 minutes for 10,000 records  
✅ **Validated**: Checks record counts and spot-checks random records  

---

## Why Do We Need This?

**Current Deployment Status:**
- ✅ New code is deployed to Cloud Run
- ✅ Using `VECTOR_BACKEND=legacy` (safe mode)
- ✅ Everything works exactly as before

**What the migration enables:**
- Switch from `VECTOR_BACKEND=legacy` to `VECTOR_BACKEND=postgres`
- Use the new, better langchain-postgres library
- Get Cloud SQL IAM authentication (more secure)
- Better performance and maintenance

---

## What Happens If You DON'T Migrate?

**Nothing breaks!** 

The system is currently running with `VECTOR_BACKEND=legacy`, which means:
- Uses the old table (`hansard_speeches`)
- Everything works exactly as it did before
- You can stay like this forever if you want

The new table will just stay empty.

---

## Running the Migration

### Step 1: Dry Run (Preview - No Changes)

```bash
cd /home/user/skai-fastmcp-cloudrun

# See what WOULD happen (doesn't actually change anything)
python scripts/migrate_to_langchain_postgres.py --dry-run
```

**Output will show:**
```
✅ Source table: 10,247 records
✅ Target table: 0 records
📦 Will migrate 10,247 records in 103 batches
⏱️  Estimated time: ~5 minutes
```

### Step 2: Execute Migration

```bash
# Actually do the migration
python scripts/migrate_to_langchain_postgres.py --execute --progress
```

**Output will show:**
```
🔄 Batch 1/103 (0.97%) - ETA: 4m 52s
🔄 Batch 2/103 (1.94%) - ETA: 4m 48s
...
✅ Migration complete!
✅ Validation passed: 10,247 records in source = 10,247 in target
✅ Spot-check passed: 10 random records verified
```

### Step 3: Switch Backend (After Migration)

```bash
# Tell Cloud Run to use the new backend
gcloud run services update hansard-mcp-server \
  --region=us-central1 \
  --update-env-vars=VECTOR_BACKEND=postgres
```

---

## Rollback Plan

If anything goes wrong after switching:

```bash
# Instant rollback (<5 minutes) - switch back to legacy
gcloud run services update hansard-mcp-server \
  --region=us-central1 \
  --update-env-vars=VECTOR_BACKEND=legacy
```

The old data is still there, untouched!

---

## Real-World Analogy

**Current State:**
- Your app is like a store that uses an old filing cabinet (legacy backend)
- You've built a new, better filing cabinet (postgres backend)
- But it's empty - you need to copy the files over

**After Migration:**
- Both filing cabinets have the same files
- You can switch between them anytime
- If the new one has problems, switch back to the old one

**After Cleanup (30+ days later):**
- You've been using the new cabinet for a month
- Everything works great
- You can finally throw away the old cabinet

---

## Timeline

### Today (Migration Day)
- ⏱️ **~5 minutes**: Run migration script
- ⏱️ **~2 minutes**: Switch to new backend
- ⏱️ **~30 minutes**: Monitor and validate

### Next 48 Hours
- 👀 Monitor performance
- ✅ Validate everything works
- 🎉 Celebrate if all good!

### After 48 Hours of Stability
- 🧹 Remove legacy dependency (optional cleanup)

### After 30 Days of Stability
- 🗑️ Archive old table (optional final cleanup)

---

## What You Should Do Now

### Option 1: Run Migration Now (Recommended)

Since you've already deployed to production with legacy backend and it's working, you can safely migrate:

```bash
# 1. Preview what will happen (no changes)
python scripts/migrate_to_langchain_postgres.py --dry-run

# 2. Look good? Do it!
python scripts/migrate_to_langchain_postgres.py --execute --progress

# 3. Wait for it to finish (~5 minutes)

# 4. Switch to new backend
gcloud run services update hansard-mcp-server \
  --region=us-central1 \
  --update-env-vars=VECTOR_BACKEND=postgres

# 5. Test it works
# (use your MCP client to test search)

# 6. If problems: instant rollback
gcloud run services update hansard-mcp-server \
  --region=us-central1 \
  --update-env-vars=VECTOR_BACKEND=legacy
```

### Option 2: Wait and Do Later

Totally fine! The system is working now with legacy backend. You can:
- Keep using it as-is
- Run migration next week/month
- Never migrate (though you won't get the benefits)

---

## Questions?

**Q: Will this cause downtime?**  
A: No! The migration happens in the background. Your app keeps using the old table until you switch.

**Q: What if the migration fails?**  
A: It rolls back automatically. No data is lost or corrupted.

**Q: Can I test this first?**  
A: Yes! Use `--dry-run` to preview without making changes.

**Q: How long does it take?**  
A: ~5 minutes for 10,000 records. The script shows progress and ETA.

**Q: What if I change my mind?**  
A: Switch back to legacy backend anytime (takes <5 minutes).

**Q: Do I have to delete the old table?**  
A: No! We recommend keeping it for 30 days as a backup. After that, you can archive/delete it or keep it forever.

---

## Bottom Line

✅ **Safe**: Old data stays intact  
✅ **Fast**: Takes ~5 minutes  
✅ **Reversible**: Instant rollback if needed  
✅ **Optional**: You can do this anytime (or never)  
✅ **Validated**: Automatic checks ensure data integrity  

**The migration is like making a backup copy of your data in a new format. If the new format works better, great! If not, you still have the original.**
