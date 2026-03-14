# Runbook: Signup Failure

## Overview
Signup failures occur when the phone sales flow breaks between qualification and activation.

## Funnel Breakpoints to Check

```sql
SELECT status, COUNT(*) as count, MAX(created_at) as latest
FROM pending_signups
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY count DESC;
```

## Failure Scenarios

### Checkout Link Not Sent
- Check Twilio logs for SMS failures
- Check Resend logs for email failures
- Check `pending_signups` where `status='qualified'` and `link_sent_at IS NULL`

### Checkout Not Completed (stalled pending)
- Identify leads where `status='link_sent'` and `link_sent_at < NOW() - INTERVAL '2 hours'`
- For high-intent leads (score >= 75): resend link + create callback task
- For low-intent leads: allow to expire naturally

### Account Creation Failure
- Check `signup_leads` table for `failure_reason` and `failure_phase`
- Check Supabase Edge Function logs for `free-trial-signup` and `create-trial`
- The `signup_conversion_guard` crew should have detected this and logged a recovery recommendation

### Provisioning Failure (Stage 1 or 2)
- Check `provisioning_jobs` table for failed jobs
- Stage 1 failures: safe to retry (run `ProvisioningHandler.run_stage1`)
- Stage 2 failures: check `telecom_resource_manager` crew output first
- If phone pool is empty: run `seed-pool` Edge Function

## Safe Manual Recovery Steps

```python
# Resend checkout link (max_rescue_attempts enforced)
from ringsnap_ops_flow.deterministic.signup_handler import SignupHandler
handler = SignupHandler()
handler.resend_checkout_link("pending_signup_id_here")

# Mark account for manual review
from ringsnap_ops_flow.deterministic.provisioning_handler import ProvisioningHandler
handler = ProvisioningHandler()
handler.mark_for_manual_review("account_id", "reason")
```

## Prevention
- Monitor checkout completion rate in daily digest
- Set up outbound safe mode when rate drops below 50%
- Keep duplicate_signup_cooldown_minutes set appropriately (default: 60)
