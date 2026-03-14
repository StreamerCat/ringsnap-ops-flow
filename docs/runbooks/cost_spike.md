# Runbook: Cost Spike Response

## Overview
The ops flow logs all LLM API calls to `ops_execution_log`.
A cost spike occurs when `total_cost_today_usd` approaches or exceeds `daily_llm_budget_usd`.

## Detection
- An alert is automatically emitted at 80% of daily budget
- The daily founder digest reports total LLM cost
- The `cost_cogs_monitor` crew runs on schedule

## Investigation

```sql
-- Today's cost by module
SELECT module_name,
       COUNT(*) as executions,
       SUM(estimated_cost_cents) / 100.0 as total_cost_usd
FROM ops_execution_log
WHERE triggered_at > NOW() - INTERVAL '24 hours'
  AND status = 'completed'
GROUP BY module_name
ORDER BY total_cost_usd DESC;

-- Identify expensive single executions
SELECT id, module_name, event_type, entity_id,
       estimated_cost_cents / 100.0 as cost_usd,
       triggered_at
FROM ops_execution_log
WHERE triggered_at > NOW() - INTERVAL '24 hours'
  AND estimated_cost_cents > 10  -- > $0.10 per execution
ORDER BY estimated_cost_cents DESC
LIMIT 20;
```

## Response Actions

### Immediate (> 80% budget)
1. The system automatically blocks new executions when budget is exceeded
2. Review which module is causing the spike
3. If abuse_guard is running excessively: check for abuse detection false-positives

### Reduce Cost
1. In `ops_config.yaml`, lower `max_daily_executions` for expensive modules
2. Route more tasks to `cheap_model` (haiku) instead of `default_model` (sonnet)
3. Activate safe mode to reduce non-critical crew executions

### Increase Budget (if justified)
Edit `ops_config.yaml`:
```yaml
cost:
  daily_llm_budget_usd: 20.0  # Increase from $10
```

## Prevention
- The event_gate debounces repeated events (default: 60 seconds)
- Rate limits per module prevent runaway execution loops
- Safe mode reduces to critical-only modules automatically
- The digest reports weekly estimated cost trends
