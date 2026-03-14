from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from crewai.flow.flow import Flow, start

from ringsnap_ops_flow.adapters.posthog_client import capture as ph_capture
from ringsnap_ops_flow.config import settings
from ringsnap_ops_flow.event_gate import EVENT_TO_MODULE, get_gate
from ringsnap_ops_flow.state import OpsEvent, OpsEventType, OpsFlowState

logger = logging.getLogger(__name__)


class AmpRouterFlow(Flow[OpsFlowState]):
    """
    AMP entrypoint flow.
    Routes incoming OpsEvent to the appropriate underlying flow or crew.
    """

    @start()
    def route_event(self) -> OpsFlowState:
        event = self.state.event
        if not event:
            logger.warning("amp_router_flow.route_event called with no event")
            self.state.should_abort = True
            return self.state

        gate = get_gate()
        module = EVENT_TO_MODULE.get(event.event_type.value, "unknown")

        allowed, reason = gate.should_process(
            event_type=event.event_type.value,
            entity_id=event.entity_id,
            module_name=module,
        )

        if not allowed:
            logger.info("amp_router_flow.event_dropped event_type=%s reason=%s", event.event_type.value, reason)
            self.state.should_abort = True
            return self.state

        start_time = datetime.now(timezone.utc)

        try:
            if event.event_type == OpsEventType.QUALIFIED_LEAD:
                from ringsnap_ops_flow.flows.sales_activation_flow import SalesActivationFlow
                SalesActivationFlow(state=self.state).kickoff()

            elif event.event_type in (
                OpsEventType.PAYMENT_FAILURE,
                OpsEventType.PROVISIONING_FAILURE,
                OpsEventType.ONBOARDING_STALLED,
            ):
                from ringsnap_ops_flow.flows.recovery_flow import RecoveryFlow
                RecoveryFlow(state=self.state).kickoff()

            elif event.event_type in (OpsEventType.DAILY_DIGEST, OpsEventType.BATCHED_INSIGHTS):
                from ringsnap_ops_flow.flows.digest_flow import DigestFlow
                DigestFlow(state=self.state).kickoff()

            elif event.event_type == OpsEventType.ABUSE_RISK_SPIKE:
                context = json.dumps(event.payload, indent=2, default=str)
                if not settings.is_stub_mode:
                    from ringsnap_ops_flow.crews.abuse_guard.crew import run
                    run(context)
                else:
                    logger.info("amp_router_flow.abuse_guard_stub payload=%s", context[:100])

            elif event.event_type == OpsEventType.SIGNUP_FAILURE:
                context = json.dumps(event.payload, indent=2, default=str)
                if not settings.is_stub_mode:
                    from ringsnap_ops_flow.crews.signup_conversion_guard.crew import run
                    run(context)
                else:
                    logger.info("amp_router_flow.signup_failure_stub payload=%s", context[:100])

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            gate.record_execution(module_name=module, event_type=event.event_type.value)
            logger.info(
                "amp_router_flow.event_processed event_type=%s module=%s elapsed_s=%.2f",
                event.event_type.value,
                module,
                elapsed,
            )
            ph_capture(
                event.entity_id or event.account_id or "ringsnap-ops-flow",
                "ops_event_processed",
                {
                    "event_type": event.event_type.value,
                    "module": module,
                    "elapsed_s": round(elapsed, 2),
                    "source": event.source,
                    "environment": settings.environment,
                },
            )

        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(
                "amp_router_flow.event_failed event_type=%s module=%s elapsed_s=%.2f error=%s",
                event.event_type.value,
                module,
                elapsed,
                e,
            )
            ph_capture(
                event.entity_id or event.account_id or "ringsnap-ops-flow",
                "ops_event_failed",
                {
                    "event_type": event.event_type.value,
                    "module": module,
                    "elapsed_s": round(elapsed, 2),
                    "error": str(e)[:200],
                    "environment": settings.environment,
                },
            )
            raise

        return self.state
