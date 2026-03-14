"""
Digest Flow — daily founder digest and batched product insights.

Triggers:
- daily_founder_digest → executive_digest crew
- batched_product_insight_job → usage_product_insights crew + outbound_roi_guard crew
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from crewai.flow.flow import Flow, listen, start

from ..config import settings
from ..deterministic.funnel_tracker import FunnelTracker
from ..event_gate import get_gate
from ..state import OpsEventType, OpsFlowState

logger = logging.getLogger(__name__)


class DigestFlow(Flow[OpsFlowState]):
    """
    Assembles and delivers the daily founder digest and batched insight jobs.
    """

    @start()
    def gather_metrics(self) -> OpsFlowState:
        """Gather all metrics needed for the digest."""
        tracker = FunnelTracker()
        gate = get_gate()

        bp = tracker.get_breakpoints(since_hours=24)

        self.state.digest.date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.state.digest.qualified_leads = bp.qualified
        self.state.digest.checkout_links_sent = bp.link_sent
        self.state.digest.checkout_completed = bp.checkout_completed
        self.state.digest.trials_activated = bp.activated
        self.state.digest.activation_failures = bp.failed
        self.state.digest.stalled_pending_signups = tracker.get_stalled_count()
        self.state.digest.estimated_waste_prevented_usd = tracker.estimated_waste_prevented_usd()

        # Cost metrics from execution counters
        self.state.digest.total_llm_cost_usd = gate.get_daily_cost_usd()
        self.state.digest.executions_by_module = gate.get_daily_counts()

        # Health flags
        self.state.digest.safe_mode_active = gate.is_safe_mode()
        self.state.digest.outbound_pause_recommended = bp.should_activate_safe_mode()
        self.state.digest.stage2_paused = self.state.provisioning.stage2_globally_paused

        logger.info("digest_flow.metrics_gathered date=%s", self.state.digest.date)
        return self.state

    @listen(gather_metrics)
    def run_product_insights(self) -> OpsFlowState:
        """Run batched product insight job if event is batched_product_insight_job."""
        event = self.state.event
        if event and event.event_type == OpsEventType.BATCHED_INSIGHTS:
            usage_context = json.dumps(
                {
                    "funnel": self.state.digest.dict(),
                    "period": "last_24h",
                },
                indent=2,
                default=str,
            )
            if not settings.is_stub_mode:
                from ..crews.usage_product_insights.crew import run as insights_run
                from ..crews.outbound_roi_guard.crew import run as roi_run
                insights_result = insights_run(usage_context)
                roi_result = roi_run(usage_context)
                self.state.crew_result = insights_result
            else:
                logger.info("digest_flow.product_insights_stub")

        return self.state

    @listen(run_product_insights)
    def write_digest(self) -> OpsFlowState:
        """Run executive_digest crew to produce the final founder digest."""
        event = self.state.event
        if not (event and event.event_type in (OpsEventType.DAILY_DIGEST, OpsEventType.BATCHED_INSIGHTS)):
            return self.state

        metrics = {
            "qualified_leads": self.state.digest.qualified_leads,
            "checkout_links_sent": self.state.digest.checkout_links_sent,
            "checkout_completed": self.state.digest.checkout_completed,
            "trials_activated": self.state.digest.trials_activated,
            "activation_failures": self.state.digest.activation_failures,
            "stalled_pending_signups": self.state.digest.stalled_pending_signups,
            "failed_recovery_count": self.state.digest.failed_recovery_count,
            "manual_review_count": self.state.digest.manual_review_count,
            "estimated_waste_prevented_usd": self.state.digest.estimated_waste_prevented_usd,
            "total_llm_cost_usd": self.state.digest.total_llm_cost_usd,
            "executions_by_module": self.state.digest.executions_by_module,
            "safe_mode_active": self.state.digest.safe_mode_active,
            "stage2_paused": self.state.digest.stage2_paused,
            "outbound_pause_recommended": self.state.digest.outbound_pause_recommended,
            "checkout_completion_rate": (
                self.state.digest.checkout_completed / self.state.digest.checkout_links_sent
                if self.state.digest.checkout_links_sent > 0
                else 1.0
            ),
            "activation_rate": (
                self.state.digest.trials_activated / self.state.digest.checkout_completed
                if self.state.digest.checkout_completed > 0
                else 1.0
            ),
        }

        if not settings.is_stub_mode:
            from ..crews.executive_digest.crew import run as digest_run
            digest_markdown = digest_run(metrics=metrics, date=self.state.digest.date or "")
        else:
            from ..tools.digest_tool import DigestFormatterTool
            digest_markdown = DigestFormatterTool()._run(
                metrics=metrics, date=self.state.digest.date or ""
            )
            digest_markdown += "\n\n## Today's Priority Actions\n1. Review pending signups.\n2. Check campaign health.\n"

        self.state.digest.digest_markdown = digest_markdown
        self.state.digest.generated_at = datetime.now(timezone.utc)

        logger.info("digest_flow.digest_written chars=%d", len(digest_markdown))
        return self.state
