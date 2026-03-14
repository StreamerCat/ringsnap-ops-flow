# Runbook: Onboarding Stall

## Overview
Onboarding is considered stalled when an activated account has not progressed past the
configured `onboarding_stall_threshold_hours` (default: 24 hours).

## Detection
The `onboarding_activation` crew automatically triggers on the `onboarding_stalled` event.
The event is fired by the ops flow when it detects accounts with no recent activity.

## Manual Investigation

```sql
-- Find stalled accounts
SELECT id, company_name, onboarding_status, updated_at,
       EXTRACT(EPOCH FROM (NOW() - updated_at))/3600 as hours_since_update
FROM accounts
WHERE subscription_status IN ('trial', 'active')
  AND onboarding_status NOT IN ('active', 'provision_failed')
  AND updated_at < NOW() - INTERVAL '24 hours'
ORDER BY updated_at ASC;
```

## Recovery Actions (Safe)

1. **Reopen task**: Call `OnboardingHandler.reopen_stalled_task(account_id)`
2. **Send reminder**: Trigger the `send-onboarding-sms` Edge Function manually
3. **Recommend callback**: If lead score >= 75, create callback task in CRM
4. **Escalate to support**: For high-value accounts, create urgent support ticket

## When to Escalate
- Account stalled > 48 hours after activation
- Multiple reopen attempts have failed
- Customer has contacted support about setup confusion

## Do Not
- Delete provisioning records to "restart" onboarding
- Release the phone number
- Cancel the trial without customer consent
