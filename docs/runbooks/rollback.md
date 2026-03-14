# Runbook: Rollback

## When to Use
- The ops flow is causing problems and needs to be disabled immediately
- You need to revert to the previous state before ops flow was added
- A critical bug is found in the ops flow service

## Rollback Steps

### Step 1: Stop the service (instant, zero downtime for existing stack)
```bash
docker stop ringsnap-ops-flow
# OR if running as process:
pkill -f "ringsnap_ops_flow"
```
The existing RingSnap TypeScript stack continues operating normally.

### Step 2: Disable webhook forwarding (prevents Supabase from calling ops service)
In Supabase project settings or function environment:
```
OPS_FLOW_ENABLED=false
```
Redeploy the forwarding Edge Function with this variable set.

### Step 3 (optional): Database rollback
Only needed if you want to remove the two new tables.
This is safe — no existing tables are affected.

```sql
-- Run in Supabase SQL editor or via psql
-- File: supabase/migrations/rollback/rollback_ops_tables.sql

DROP TABLE IF EXISTS ops_execution_log CASCADE;
DROP TABLE IF EXISTS pending_signups CASCADE;
```

### Step 4: Git rollback (optional)
If you want to remove all ops flow code from the repo:
```bash
git revert <commit-hash>
# OR
git checkout main -- .
git rm -rf ringsnap_ops_flow/
git rm supabase/migrations/20260313000001_ringsnap_ops_pending_signups.sql
git rm supabase/migrations/20260313000002_ringsnap_ops_execution_log.sql
```

## Verification
After rollback:
- [ ] `curl https://your-app.com/health` returns 200 (existing app healthy)
- [ ] Stripe webhooks still processing
- [ ] Vapi calls still working
- [ ] No errors in Supabase logs

## Notes
- Pending signups in the database will remain but no new ones will be created
- Existing accounts are not affected
- The rollback is fully reversible (you can redeploy the ops service at any time)
