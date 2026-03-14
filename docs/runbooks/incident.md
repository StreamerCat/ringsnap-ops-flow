# Runbook: Incident Response

## Severity Levels

| Severity | Examples | Response Time |
|----------|---------|---------------|
| Critical | Service down, data loss risk, payment processing broken | Immediate |
| High | Activation failures > 20%, provisioning down, abuse spike | 15 minutes |
| Medium | Onboarding stalls, checkout rate below threshold, digest not sending | 1 hour |
| Low | Cost spike, rate limit hit, minor triage errors | Next business day |

## General Incident Steps

1. **Check health endpoint**: `GET /ops/health` — verify service is running
2. **Check status endpoint**: `GET /ops/status` — check execution counts and cost
3. **Check logs**: Review service logs for errors
4. **Check alerts**: Review any critical alerts in `ops_execution_log` table

## Specific Scenarios

### Service Not Responding
```bash
# Check if running
docker ps | grep ringsnap-ops-flow

# View logs
docker logs ringsnap-ops-flow --tail 100

# Restart
docker restart ringsnap-ops-flow
```

### High Error Rate in Activation
1. Check `ops_execution_log` for recent `activation_recovery` entries with `status=failed`
2. Check `pending_signups` for accounts stuck in `checkout_completed` state
3. If provisioning failure rate > 15%: pause Stage 2 manually
4. See `signup_failure.md` runbook for specific steps

### Budget Alert (LLM cost spike)
See `cost_spike.md` runbook.

### Abuse Spike
1. Check `ops_execution_log` for `abuse_guard` entries
2. Review recommendation in `metadata` field
3. All `block_account` recommendations require human approval before execution
4. To throttle: set `max_daily_executions.abuse_guard` lower in `ops_config.yaml`
