# Runbook: Outbound Pause

## When to Pause Outbound
Outbound calling should be paused or reduced when:
- Checkout completion rate drops below 50% (threshold: `checkout_completion_threshold`)
- Activation failure rate exceeds 20% (threshold: `activation_failure_threshold`)
- Stage 2 provisioning is paused (can't fulfill new trials)
- The `outbound_roi_guard` crew recommends safe mode

## How to Pause

### Option 1: Outbound Safe Mode (reduce, don't stop)
Set in `ops_config.yaml` or via environment:
```yaml
# ops_config.yaml
# Triggers safe mode logic in event_gate.py
```
Or call the gate directly:
```python
from ringsnap_ops_flow.event_gate import get_gate
get_gate().activate_safe_mode()
```

### Option 2: Pause Vapi Outbound Campaigns
In Vapi dashboard: pause the outbound campaign.
This is the recommended approach for rapid response.

### Option 3: Reduce Call Volume
In ops_config.yaml, lower `max_daily_executions.sales_triage` to reduce
the number of qualified leads processed per day.

## Verification Before Resuming
Before resuming full outbound volume:
- [ ] Checkout completion rate > 50%
- [ ] Activation failure rate < 20%
- [ ] Stage 2 provisioning unpaused
- [ ] At least 3 consecutive days of healthy metrics

## Resume Outbound
```python
from ringsnap_ops_flow.event_gate import get_gate
get_gate().deactivate_safe_mode()
```
