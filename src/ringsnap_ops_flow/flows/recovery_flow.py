"""
Recovery Flow — handles payment, provisioning, and onboarding failures.

Triggers:
- payment_failure → activation_recovery crew
- provisioning_failure → activation_recovery crew + telecom_resource_manager crew
- onboarding_stalled → onboarding_activation crew
"""

from __future__ import annotations

import json
import logging

from crewai.flow.flow import Flow, listen, start

from ..adapters.posthog_client import capture as ph_capture
from ..config import settings
from ..deterministic.onboarding_handler import OnboardingHandler
from ..deterministic.provisioning_handler import ProvisioningHandler, pause_stage2
from ..deterministic.retry_handler import RetryCappedError, attempt_retry
from ..state import AlertSeverity, OpsEventType, OpsFlowState

logger = logging.getLogger(__name__)


class RecoveryFlow(Flow[OpsFlowState]):
    """
    Routes failure events to the appropriate recovery crew and executes safe auto-fixes.
    """

    @start()
    def route_failure(self) -> OpsFlowState:
        """Route to appropriate recovery crew based on event type."""
        event = self.state.event
        if not event:
            self.state.should_abort = True
            return self.state

        event_type = event.event_type
        payload = event.payload
        account_id = event.account_id or ""

        if event_type == OpsEventType.PAYMENT_FAILURE:
            self._handle_payment_failure(account_id, payload)
        elif event_type == OpsEventType.PROVISIONING_FAILURE:
            self._handle_provisioning_failure(account_id, payload)
        elif event_type == OpsEventType.ONBOARDING_STALLED:
            self._handle_onboarding_stall(account_id, payload)
        else:
            logger.warning("recovery_flow.unknown_event_type event_type=%s", event_type)

        ph_capture(
            account_id or "ringsnap-ops-flow",
            "ops_recovery_started",
            {
                "event_type": event_type.value if hasattr(event_type, "value") else str(event_type),
                "account_id": account_id,
                "environment": settings.environment,
            },
        )
        return self.state

    @listen(route_failure)
    def apply_safe_auto_fixes(self) -> OpsFlowState:
        """Execute any safe non-destructive fixes recommended by the recovery crew."""
        if self.state.should_abort:
            return self.state

        result_str = self.state.crew_result or ""
        if not result_str:
            return self.state

        try:
            result = json.loads(result_str)
        except (json.JSONDecodeError, TypeError):
            return self.state

        account_id = self.state.event.account_id or "" if self.state.event else ""

        # Apply safe auto-fixes from recovery plan
        recovery_action = result.get("recovery_action", "")
        safe_to_auto = result.get("safe_to_auto_execute", False)

        if safe_to_auto and recovery_action == "retry_stage1" and account_id:
            handler = ProvisioningHandler()
            try:
                attempt_retry(
                    fn=lambda: handler.run_stage1(account_id, ""),
                    entity_id=account_id,
                    step="stage1_recovery",
                    max_attempts=2,  # Reduced cap for recovery path
                )
                logger.info("recovery_flow.stage1_retry_succeeded account_id=%s", account_id)
                ph_capture(
                    account_id,
                    "ops_recovery_auto_fixed",
                    {
                        "account_id": account_id,
                        "recovery_action": recovery_action,
                        "environment": settings.environment,
                    },
                )
            except RetryCappedError:
                handler.mark_for_manual_review(account_id, "stage1_recovery_capped")
                self.state.alerts.add(
                    severity=AlertSeverity.CRITICAL,
                    message=f"Stage 1 recovery retry cap reached for account {account_id}",
                    module="recovery_flow",
                    entity_id=account_id,
                )

        # Check if Stage 2 should be paused globally
        if result.get("pause_stage2_recommended", False):
            pause_stage2(reason="activation_recovery_crew_recommendation")
            self.state.provisioning.stage2_globally_paused = True
            self.state.alerts.add(
                severity=AlertSeverity.WARNING,
                message="Stage 2 provisioning paused due to high failure rate",
                module="recovery_flow",
            )

        return self.state

    def _handle_payment_failure(self, account_id: str, payload: dict) -> None:
        failure_context = json.dumps(
            {
                "event_type": "payment_failure",
                "account_id": account_id,
                "invoice_id": payload.get("invoice_id", "unknown"),
                "failure_reason": payload.get("failure_reason", "unknown"),
            },
            indent=2,
        )

        if not settings.is_stub_mode:
            from ..crews.activation_recovery.crew import run
            result = run(failure_context)
            self.state.crew_result = result
        else:
            self.state.crew_result = json.dumps(
                {
                    "failure_type": "payment",
                    "recovery_action": "no_action",
                    "safe_to_auto_execute": False,
                    "alert_severity": "warning",
                    "summary": "[stub] Payment failure logged.",
                }
            )

    def _handle_provisioning_failure(self, account_id: str, payload: dict) -> None:
        telecom_context = json.dumps(
            {
                "event_type": "provisioning_failure",
                "account_id": account_id,
                "failure_step": payload.get("failure_step", "unknown"),
                "error": payload.get("error", "unknown"),
            },
            indent=2,
        )

        failure_context = telecom_context  # reuse for activation_recovery crew

        if not settings.is_stub_mode:
            from ..crews.activation_recovery.crew import run as recovery_run
            from ..crews.telecom_resource_manager.crew import run as telecom_run
            telecom_result = telecom_run(telecom_context)
            recovery_result = recovery_run(failure_context)
            self.state.crew_result = recovery_result
        else:
            self.state.crew_result = json.dumps(
                {
                    "failure_type": "provisioning",
                    "recovery_action": "retry_stage1",
                    "safe_to_auto_execute": True,
                    "alert_severity": "warning",
                    "pause_stage2_recommended": False,
                    "summary": "[stub] Provisioning failure — retry stage1.",
                }
            )

    def _handle_onboarding_stall(self, account_id: str, payload: dict) -> None:
        stall_context = json.dumps(
            {
                "event_type": "onboarding_stalled",
                "account_id": account_id,
                "stall_hours": payload.get("stall_hours", 0),
                "last_completed_step": payload.get("last_completed_step", "unknown"),
            },
            indent=2,
        )

        if not settings.is_stub_mode:
            from ..crews.onboarding_activation.crew import run
            result_str = run(stall_context)
            self.state.crew_result = result_str
            try:
                result = json.loads(result_str)
                if result.get("safe_to_auto_execute") and result.get("recovery_action") == "reopen_task":
                    handler = OnboardingHandler()
                    handler.reopen_stalled_task(account_id)
                    logger.info("recovery_flow.onboarding_task_reopened account_id=%s", account_id)
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            handler = OnboardingHandler()
            handler.reopen_stalled_task(account_id)
            self.state.crew_result = json.dumps({"recovery_action": "reopen_task", "safe_to_auto_execute": True})
