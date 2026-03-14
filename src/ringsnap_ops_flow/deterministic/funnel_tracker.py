"""
Funnel tracker — deterministic funnel state counting and conversion rate calculation.

Reads from pending_signups table to compute rates.
No LLM calls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import thresholds
from ..state import PendingSignupStatus

logger = logging.getLogger(__name__)


class FunnelBreakpoints:
    """Snapshot of funnel counts and conversion rates."""

    def __init__(self, counts: dict[str, int]):
        self.counts = counts
        self.qualified = counts.get(PendingSignupStatus.QUALIFIED, 0)
        self.link_sent = counts.get(PendingSignupStatus.LINK_SENT, 0)
        self.checkout_opened = counts.get(PendingSignupStatus.CHECKOUT_OPENED, 0)
        self.checkout_completed = counts.get(PendingSignupStatus.CHECKOUT_COMPLETED, 0)
        self.account_created = counts.get(PendingSignupStatus.ACCOUNT_CREATED, 0)
        self.provisioned = counts.get(PendingSignupStatus.PROVISIONED, 0)
        self.activated = counts.get(PendingSignupStatus.ACTIVATED, 0)
        self.expired = counts.get(PendingSignupStatus.EXPIRED, 0)
        self.failed = counts.get(PendingSignupStatus.FAILED, 0)

    @property
    def total_started(self) -> int:
        return sum(self.counts.values())

    @property
    def checkout_completion_rate(self) -> float:
        """Ratio of checkout_completed / link_sent."""
        if self.link_sent == 0:
            return 1.0  # No data yet — assume healthy
        return min(1.0, self.checkout_completed / self.link_sent)

    @property
    def activation_rate(self) -> float:
        """Ratio of activated / checkout_completed."""
        if self.checkout_completed == 0:
            return 1.0
        return min(1.0, self.activated / self.checkout_completed)

    @property
    def provisioning_success_rate(self) -> float:
        """Ratio of provisioned / account_created."""
        if self.account_created == 0:
            return 1.0
        return min(1.0, self.provisioned / self.account_created)

    def is_checkout_below_threshold(self) -> bool:
        return self.checkout_completion_rate < thresholds.checkout_completion_threshold

    def is_activation_below_threshold(self) -> bool:
        return self.activation_rate < (1.0 - thresholds.activation_failure_threshold)

    def is_provisioning_below_threshold(self) -> bool:
        return self.provisioning_success_rate < (1.0 - thresholds.expensive_provisioning_failure_threshold)

    def should_activate_safe_mode(self) -> bool:
        return (
            self.is_checkout_below_threshold()
            or self.is_activation_below_threshold()
            or self.is_provisioning_below_threshold()
        )

    def to_dict(self) -> dict:
        return {
            "counts": self.counts,
            "checkout_completion_rate": round(self.checkout_completion_rate, 4),
            "activation_rate": round(self.activation_rate, 4),
            "provisioning_success_rate": round(self.provisioning_success_rate, 4),
            "safe_mode_recommended": self.should_activate_safe_mode(),
        }


class FunnelTracker:
    """
    Reads pending_signups to track funnel health.
    In stub mode, returns synthetic healthy data.
    """

    def __init__(self, supabase_adapter=None):
        self._supabase = supabase_adapter

    def get_breakpoints(self, since_hours: int = 24) -> FunnelBreakpoints:
        """Get funnel counts for the last `since_hours` hours."""
        if self._supabase is None or self._supabase.is_stub:
            return self._stub_breakpoints()

        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        # TODO: query pending_signups grouped by status
        counts: dict[str, int] = {}
        try:
            rows = self._supabase.query(
                "pending_signups",
                filters={"created_at": f"gte.{since.isoformat()}"},
            )
            for row in rows:
                status = row.get("status", "unknown")
                counts[status] = counts.get(status, 0) + 1
        except Exception as e:
            logger.error("funnel_tracker.query_failed error=%s", e)

        return FunnelBreakpoints(counts)

    def record_transition(
        self,
        pending_signup_id: str,
        from_status: str,
        to_status: str,
    ) -> None:
        """Log a status transition. Used for audit trail."""
        logger.info(
            "funnel_tracker.transition id=%s from=%s to=%s",
            pending_signup_id,
            from_status,
            to_status,
        )
        # TODO: write to system_events table for audit trail

    def get_stalled_count(self, since_hours: Optional[int] = None) -> int:
        """Count pending signups that have not progressed beyond link_sent."""
        hours = since_hours or 48
        if self._supabase is None or self._supabase.is_stub:
            return 0
        # TODO: query pending_signups where status IN ('qualified','link_sent')
        # and created_at < NOW() - INTERVAL hours
        return 0

    def estimated_waste_prevented_usd(self, since_hours: int = 24) -> float:
        """
        Estimate USD value of expensive provisioning NOT wasted on unqualified leads.
        Conservative estimate: $2 per prevented Stage 2 provisioning.
        """
        bp = self.get_breakpoints(since_hours)
        # Leads who got link sent but didn't complete checkout = saved from Stage 2
        prevented = max(0, bp.link_sent - bp.checkout_completed)
        cost_per_prevention = 2.0  # conservative estimate
        return prevented * cost_per_prevention

    def _stub_breakpoints(self) -> FunnelBreakpoints:
        return FunnelBreakpoints(
            {
                PendingSignupStatus.QUALIFIED: 5,
                PendingSignupStatus.LINK_SENT: 4,
                PendingSignupStatus.CHECKOUT_COMPLETED: 3,
                PendingSignupStatus.ACTIVATED: 2,
            }
        )
