# RingSnap Ops Flow — Phase 1 GTM Ops

CrewAI Flow-based orchestration control plane for RingSnap outbound phone sales → trial activation → onboarding.

## Architecture

```
Vapi outbound call
    │ tool call (qualified lead)
    ▼
Supabase Edge Functions (existing TypeScript stack — unchanged)
    │ POST /ops/event  (only for high-value events, gated by OPS_FLOW_ENABLED)
    ▼
ringsnap_ops_flow FastAPI service
    │ event_gate.py (allowlist + rate limit + debounce + budget check)
    ▼
CrewAI Flow routes to appropriate crew
    │
    ├── SalesActivationFlow  →  sales_triage crew  →  deterministic signup/checkout/provisioning
    ├── RecoveryFlow         →  activation_recovery / onboarding_activation / telecom_resource_manager
    └── DigestFlow           →  executive_digest / usage_product_insights
```

**Key principle**: CrewAI only runs on 8 approved high-value events. Everything else is deterministic Python.

## Quick Start (Remote Environment)

```bash
cd ringsnap_ops_flow

# Install dependencies
pip install poetry
poetry install

# Configure environment
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and SUPABASE_SERVICE_ROLE_KEY

# Run tests (works without real credentials — all adapters have stub mode)
poetry run pytest tests/ -v

# Start the service
poetry run ringsnap-ops
# OR
poetry run uvicorn ringsnap_ops_flow.main:app --host 0.0.0.0 --port 8080 --reload

# Health check
curl http://localhost:8080/ops/health

# Status (execution counts + cost)
curl http://localhost:8080/ops/status
```

## Run with Docker

```bash
cp .env.example .env
# Edit .env

docker-compose up --build

# Health check
curl http://localhost:8080/ops/health
```

## Run Tests

```bash
# All tests (stub mode — no credentials needed)
poetry run pytest tests/ -v

# Specific test files
poetry run pytest tests/test_event_gate.py -v
poetry run pytest tests/voice_qa/ -v

# With coverage
poetry run pytest tests/ --cov=ringsnap_ops_flow --cov-report=term-missing
```

## Rollback

See `docs/runbooks/rollback.md` for full rollback procedure.

**TL;DR:**
1. `docker stop ringsnap-ops-flow` — existing stack unaffected
2. Set `OPS_FLOW_ENABLED=false` in Supabase function env to stop event forwarding
3. DB rollback (optional): `psql $DATABASE_URL -f supabase/migrations/rollback/rollback_ops_tables.sql`

## Directory Structure

```
ringsnap_ops_flow/
├── config/
│   └── ops_config.yaml          ← All thresholds, model routing, cost limits
├── src/ringsnap_ops_flow/
│   ├── main.py                  ← FastAPI app + AMP entrypoint
│   ├── state.py                 ← Pydantic shared state schema
│   ├── event_gate.py            ← Central CrewAI invocation guard
│   ├── config.py                ← Settings loader
│   ├── flows/                   ← 3 CrewAI Flows
│   ├── crews/                   ← 12 CrewAI Crew modules
│   ├── adapters/                ← 6 external service adapters (stub-safe)
│   ├── deterministic/           ← 5 deterministic handlers (no LLM)
│   └── tools/                   ← 3 CrewAI tools
├── tests/
│   ├── test_event_gate.py       ← Golden tests for event gating
│   ├── test_signup_handler.py   ← Golden tests for signup flow
│   ├── test_payment_handler.py  ← Golden tests for payment handling
│   ├── test_provisioning_handler.py ← Golden tests for provisioning gates
│   └── voice_qa/                ← Voice prompt QA scaffold
└── docs/runbooks/               ← 6 operational runbooks
```

## Approved Event Types

Only these 8 events trigger CrewAI:

| Event | Crew(s) | Model Tier |
|-------|---------|-----------|
| `qualified_lead_wants_trial_or_paid` | sales_triage | cheap (haiku) |
| `payment_failure` | activation_recovery | default (sonnet) |
| `signup_or_account_creation_failure` | signup_conversion_guard | cheap |
| `provisioning_failure` | activation_recovery + telecom_resource_manager | default |
| `onboarding_stalled` | onboarding_activation | cheap |
| `abuse_or_risk_spike` | abuse_guard | default |
| `daily_founder_digest` | executive_digest | default |
| `batched_product_insight_job` | usage_product_insights + outbound_roi_guard | cheap |

## Cost Controls

- Daily LLM budget: $10/day (configurable in `ops_config.yaml`)
- Alert at 80% of budget
- All executions logged to `ops_execution_log` table
- Safe mode: reduces to critical-only modules when health degrades
- Per-module daily execution caps

## What I Need From You

1. **ANTHROPIC_API_KEY** — for CrewAI LLM calls
2. **SUPABASE_SERVICE_ROLE_KEY** — to connect to database
3. **STRIPE_SECRET_KEY** — for checkout session creation
4. **OPS_WEBHOOK_SECRET** — to secure the webhook endpoint
5. **TWILIO credentials** — for SMS delivery (optional, skipped in stub mode)

## AMP Deployment

```bash
# Install CrewAI CLI
pip install crewai

# Deploy to CrewAI AMP
crewai deploy --config crewai.yaml
```
