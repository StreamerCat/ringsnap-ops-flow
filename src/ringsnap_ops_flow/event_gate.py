"""
Event Gate — Central allowlist and rate limiter for CrewAI crew invocations.

Rules:
1. Only events in ALLOWED_EVENTS trigger CrewAI.
2. Per-module daily execution count must be below limit.
3. Same event+entity must not have fired within debounce_seconds.
4. Daily LLM budget must not be exceeded.
5. If safe_mode_active, only critical modules are allowed.

All checks are logged. Gate drops silently (no exceptions to callers).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from .adapters.posthog_client import capture as ph_capture
from .config import cost as cost_cfg
from .config import crews as crews_cfg
from .config import execution as exec_cfg
from .config import safe_mode_cfg
from .config import settings
from .state import AlertSeverity, AlertState, OpsEventType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed event types — the only events that may trigger CrewAI
# ---------------------------------------------------------------------------

ALLOWED_EVENTS: frozenset[str] = frozenset(e.value for e in OpsEventType)

# Map from event type → which crew module handles it
EVENT_TO_MODULE: dict[str, str] = {
    OpsEventType.QUALIFIED_LEAD.value: "sales_triage",
    OpsEventType.PAYMENT_FAILURE.value: "activation_recovery",
    OpsEventType.SIGNUP_FAILURE.value: "signup_conversion_guard",
    OpsEventType.PROVISIONING_FAILURE.value: "activation_recovery",
    OpsEventType.ONBOARDING_STALLED.value: "onboarding_activation",
    OpsEventType.ABUSE_RISK_SPIKE.value: "abuse_guard",
    OpsEventType.DAILY_DIGEST.value: "executive_digest",
    OpsEventType.BATCHED_INSIGHTS.value: "usage_product_insights",
}


class EventGate:
    """
    Stateful gate that decides whether an incoming event should trigger a crew.

    In production, debounce state and counters are backed by ops_execution_log in Supabase.
    In stub mode (no DB connection), uses in-memory dictionaries.
    """

    def __init__(self, supabase_adapter=None):
        self._supabase = supabase_adapter
        # In-memory fallback for stub/test mode
        self._debounce_cache: dict[str, datetime] = {}
        self._daily_counts: dict[str, int] = {}
        self._daily_cost_usd: float = 0.0
        self._safe_mode_active: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_process(
        self,
        event_type: str,
        entity_id: Optional[str] = None,
        module_name: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Returns (True, "") if the event should be processed,
        or (False, reason) if it should be dropped.
        """
        if not settings.ops_flow_enabled:
            return False, "ops_flow_disabled"

        module = module_name or EVENT_TO_MODULE.get(event_type, "unknown")

        checks = [
            self._check_allowlist(event_type),
            self._check_safe_mode(module),
            self._check_daily_budget(),
            self._check_module_rate_limit(module),
            self._check_debounce(event_type, entity_id),
        ]

        for allowed, reason in checks:
            if not allowed:
                logger.info(
                    "event_gate.dropped event_type=%s entity_id=%s module=%s reason=%s",
                    event_type,
                    entity_id,
                    module,
                    reason,
                )
                ph_capture(
                    entity_id or "ringsnap-ops-flow",
                    "ops_event_dropped",
                    {
                        "event_type": event_type,
                        "module": module,
                        "drop_reason": reason,
                        "environment": settings.environment,
                    },
                )
                return False, reason

        logger.info(
            "event_gate.allowed event_type=%s entity_id=%s module=%s",
            event_type,
            entity_id,
            module,
        )
        ph_capture(
            entity_id or "ringsnap-ops-flow",
            "ops_event_accepted",
            {
                "event_type": event_type,
                "module": module,
                "environment": settings.environment,
            },
        )
        return True, ""

    def record_execution(
        self,
        module_name: str,
        cost_usd: float = 0.0,
        event_type: str = "",
        entity_id: Optional[str] = None,
    ) -> None:
        """Called after a crew finishes to update counters."""
        self._daily_counts[module_name] = self._daily_counts.get(module_name, 0) + 1
        self._daily_cost_usd += cost_usd

        if self._daily_cost_usd >= cost_cfg.daily_llm_budget_usd * cost_cfg.alert_at_pct:
            if not getattr(self, "_budget_alert_fired", False):
                self._budget_alert_fired = True
                logger.warning(
                    "event_gate.budget_alert total_cost_usd=%.4f budget_usd=%.2f",
                    self._daily_cost_usd,
                    cost_cfg.daily_llm_budget_usd,
                )
                ph_capture(
                    "ringsnap-ops-flow",
                    "ops_budget_alert",
                    {
                        "daily_cost_usd": round(self._daily_cost_usd, 4),
                        "budget_usd": cost_cfg.daily_llm_budget_usd,
                        "pct_used": round(self._daily_cost_usd / cost_cfg.daily_llm_budget_usd, 2),
                        "environment": settings.environment,
                    },
                )

    def activate_safe_mode(self) -> None:
        self._safe_mode_active = True
        logger.warning("event_gate.safe_mode_activated")
        ph_capture(
            "ringsnap-ops-flow",
            "ops_safe_mode_activated",
            {
                "daily_cost_usd": round(self._daily_cost_usd, 4),
                "environment": settings.environment,
            },
        )

    def deactivate_safe_mode(self) -> None:
        self._safe_mode_active = False
        logger.info("event_gate.safe_mode_deactivated")
        ph_capture(
            "ringsnap-ops-flow",
            "ops_safe_mode_deactivated",
            {"environment": settings.environment},
        )

    def is_safe_mode(self) -> bool:
        return self._safe_mode_active

    def get_daily_counts(self) -> dict[str, int]:
        return dict(self._daily_counts)

    def get_daily_cost_usd(self) -> float:
        return self._daily_cost_usd

    def reset_daily_counters(self) -> None:
        """Call at midnight / start of new UTC day."""
        self._daily_counts = {}
        self._daily_cost_usd = 0.0
        self._debounce_cache = {}
        self._budget_alert_fired = False
        logger.info("event_gate.daily_counters_reset")

    # ------------------------------------------------------------------
    # Private checks — each returns (allowed: bool, reason: str)
    # ------------------------------------------------------------------

    def _check_allowlist(self, event_type: str) -> tuple[bool, str]:
        if event_type not in ALLOWED_EVENTS:
            return False, "not_in_allowlist"
        return True, ""

    def _check_safe_mode(self, module_name: str) -> tuple[bool, str]:
        if self._safe_mode_active and module_name not in safe_mode_cfg.critical_only_modules:
            return False, "safe_mode_non_critical"
        return True, ""

    def _check_daily_budget(self) -> tuple[bool, str]:
        if self._daily_cost_usd >= cost_cfg.daily_llm_budget_usd:
            return False, "budget_exceeded"
        return True, ""

    def _check_module_rate_limit(self, module_name: str) -> tuple[bool, str]:
        limit = crews_cfg.get_max_daily(module_name)
        count = self._daily_counts.get(module_name, 0)
        if count >= limit:
            return False, f"rate_limit_hit:{module_name}"
        return True, ""

    def _check_debounce(self, event_type: str, entity_id: Optional[str]) -> tuple[bool, str]:
        key = f"{event_type}:{entity_id or '_'}"
        now = datetime.now(timezone.utc)
        last_seen = self._debounce_cache.get(key)
        if last_seen is not None:
            elapsed = (now - last_seen).total_seconds()
            if elapsed < exec_cfg.debounce_seconds:
                return False, f"debounce:{elapsed:.0f}s_ago"
        self._debounce_cache[key] = now
        return True, ""


# Module-level singleton — shared across the FastAPI app lifetime
_gate_instance: Optional[EventGate] = None


def get_gate() -> EventGate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = EventGate()
    return _gate_instance
