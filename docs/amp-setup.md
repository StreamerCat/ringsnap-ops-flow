# CrewAI AMP + Supabase Bridge — Setup Guide

Non-dev-friendly step-by-step. Complete these in order.

---

## 1 · AMP Readiness Check

The project is **ready for AMP deployment as-is**. Nothing needs to change.

| Check | Status | Note |
|---|---|---|
| `crewai.yaml` present | ✅ | entrypoint: `src/ringsnap_ops_flow/main.py` |
| Python 3.12 pinned | ✅ | `pyproject.toml` `python = ">=3.12,<3.13"` |
| AMP entrypoint class | ✅ | `RingSnapOpsFlow.kickoff(event_data)` in `main.py` |
| Stub mode (no creds = safe) | ✅ | All adapters skip gracefully |
| Daily budget guard ($10/day) | ✅ | `event_gate.py` |
| OPS_FLOW_ENABLED kill switch | ✅ | Set to `"false"` to pause without redeploying |

---

## 2 · AMP Environment Variables

Set these in the **CrewAI AMP dashboard → your deployment → Environment Variables**.

| Variable | Required | Example value | What it is |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | `sk-ant-api03-…` | LLM for all crews |
| `SUPABASE_URL` | **Yes** | `https://xxxx.supabase.co` | Your production Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | `eyJ…` | Service role key — keep secret |
| `OPS_WEBHOOK_SECRET` | **Yes** | generate with `openssl rand -hex 32` | Shared secret — bridge uses this to authenticate to AMP |
| `STRIPE_SECRET_KEY` | **Yes** | `sk_live_…` | Stripe for checkout session creation |
| `STRIPE_OPS_WEBHOOK_SECRET` | **Yes** | `whsec_…` | Stripe webhook signing secret (from Stripe dashboard) |
| `ENVIRONMENT` | **Yes** | `production` | Controls logging + reload behaviour |
| `OPS_FLOW_ENABLED` | **Yes** | `true` | Master kill switch — set to `false` to pause all crew execution |
| `TWILIO_ACCOUNT_SID` | Optional | `ACxxx…` | SMS delivery. Skipped if blank (stub mode) |
| `TWILIO_AUTH_TOKEN` | Optional | `…` | Twilio auth |
| `TWILIO_FROM_NUMBER` | Optional | `+15551234567` | Twilio outbound number |
| `RESEND_API_KEY` | Optional | `re_…` | Email delivery. Skipped if blank |
| `RESEND_FROM_EMAIL` | Optional | `ops@ringsnap.com` | From address |
| `VAPI_API_KEY` | Optional | `…` | Vapi tool responses. Skipped if blank |
| `POSTHOG_API_KEY` | Optional | `phc_…` | Telemetry. Skipped if blank |

> **Generate `OPS_WEBHOOK_SECRET`**:
> ```bash
> openssl rand -hex 32
> ```
> Copy the output. You will use the same value in both AMP and Supabase.

---

## 3 · Supabase Secrets

Set these in the **Supabase Dashboard → Edge Functions → Secrets** (or via CLI).

| Secret | Value |
|---|---|
| `OPS_WEBHOOK_SECRET` | Same value you set in AMP above |
| `CREW_AMP_URL` | Your AMP kickoff URL — format: `https://[deployment-id].crewai.com/kickoff` (get this from AMP dashboard after deploying) |
| `CREW_AMP_API_KEY` | API key issued by AMP dashboard for your deployment |

**Via Supabase CLI** (fastest):
```bash
supabase secrets set OPS_WEBHOOK_SECRET=your-generated-secret
supabase secrets set CREW_AMP_URL=https://your-deployment.crewai.com/kickoff
supabase secrets set CREW_AMP_API_KEY=your-amp-api-key
```

---

## 4 · Deploy the Edge Function

The bridge lives at `supabase/functions/ops-bridge/index.ts`.

```bash
# From the repo root:
supabase functions deploy ops-bridge --no-verify-jwt
```

`--no-verify-jwt` is intentional — auth is handled by `x-ops-secret`, not Supabase JWT.

After deploy, the function URL will be:
```
https://[your-project-ref].supabase.co/functions/v1/ops-bridge
```

---

## 5 · Test One Event Manually

Replace the URL and secret with your real values:

```bash
curl -X POST \
  https://[your-project-ref].supabase.co/functions/v1/ops-bridge \
  -H "Content-Type: application/json" \
  -H "x-ops-secret: YOUR_OPS_WEBHOOK_SECRET" \
  -d '{
    "event_type": "qualified_lead",
    "entity_id": "test-lead-001",
    "source": "manual_test",
    "payload": {
      "phone": "+15551234567",
      "email": "test@example.com",
      "full_name": "Test Owner",
      "trade": "HVAC",
      "score": 82
    }
  }'
```

**Expected response:**
```json
{ "status": "forwarded", "event_type": "qualified_lead", "amp_status": 200 }
```

**If AMP is not deployed yet**, you'll get:
```json
{ "error": "AMP not configured" }
```
That's fine — deploy AMP first, then set the Supabase secrets, then re-test.

---

## 6 · Wire App Events to the Bridge

Add this to any existing Supabase edge function where a high-value event occurs.
It's a best-effort fire-and-forget — a failure here never breaks the main function.

```typescript
// Add this near the top of any function that should send ops events:
async function notifyOps(
  eventType: string,
  entityId: string | null,
  payload: Record<string, unknown>
): Promise<void> {
  const secret = Deno.env.get("OPS_WEBHOOK_SECRET");
  const bridgeUrl = `https://${Deno.env.get("SUPABASE_URL")?.split("//")[1]}/functions/v1/ops-bridge`;
  if (!secret) return; // ops not configured yet — skip silently

  try {
    await fetch(bridgeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-ops-secret": secret },
      body: JSON.stringify({ event_type: eventType, entity_id: entityId, payload }),
    });
  } catch {
    // best-effort — never throw
  }
}

// Example usage inside the function:
await notifyOps("qualified_lead", leadId, { phone, email, full_name, trade, score });
```

**Suggested wiring points:**

| Event | Where to add the call |
|---|---|
| `qualified_lead` | `vapi-tools-*` after lead scoring passes threshold |
| `signup_failure` | `create-trial` or `free-trial-signup` on failure path |
| `payment_failure` | `stripe-webhook` on `invoice.payment_failed` |
| `provisioning_failure` | `provision` or `provision-account` on failure |
| `onboarding_stalled` | `monitor-alerts` or a scheduled cron function |
| `daily_digest` | Cron job or `monitor-alerts` once per day |

---

## 7 · Verification Checklist

After deploying, verify each step:

- [ ] **AMP health**: `GET https://your-deployment.crewai.com/health` → `{"status": "ok"}`
- [ ] **AMP stub mode**: health response shows `"stub_mode": false` (means `ANTHROPIC_API_KEY` is set correctly)
- [ ] **AMP kill switch**: `OPS_FLOW_ENABLED=true` in AMP env vars
- [ ] **Bridge secrets set**: Supabase dashboard shows `OPS_WEBHOOK_SECRET`, `CREW_AMP_URL`, `CREW_AMP_API_KEY`
- [ ] **Bridge deployed**: `supabase functions list` shows `ops-bridge`
- [ ] **Manual curl test**: returns `{"status": "forwarded", "amp_status": 200}` (see section 5)
- [ ] **AMP execution log**: after curl test, check AMP dashboard logs — should show a `qualified_lead` processing run
- [ ] **Budget check**: AMP `/ops/status` endpoint → `daily_cost_usd` should be a small number after the test run
- [ ] **No production impact**: test with a fake `entity_id` first — the system will run in stub mode on unknown IDs

---

## 8 · Approved Event Types (Phase 1)

Only these 6 event types will be forwarded. All others are silently dropped at the bridge.

| Event | Triggers crew | Max/day |
|---|---|---|
| `qualified_lead` | `sales_triage` | 200 |
| `payment_failure` | `activation_recovery` | 50 |
| `signup_failure` | `signup_conversion_guard` | 50 |
| `provisioning_failure` | `activation_recovery` | 50 |
| `onboarding_stalled` | `onboarding_activation` | 50 |
| `daily_digest` | `executive_digest` | 1 |

---

## 9 · Rollback / Pause

**Instant pause (no redeploy)**:
- In AMP dashboard: set `OPS_FLOW_ENABLED=false` → all events accepted but immediately dropped

**Remove bridge entirely**:
```bash
# Remove the notifyOps() calls from app functions, or:
supabase functions delete ops-bridge
```

**Remove AMP secret to block bridge**:
```bash
supabase secrets unset CREW_AMP_URL
```
Bridge will return `503 AMP not configured` — your app functions are unaffected (fire-and-forget).
