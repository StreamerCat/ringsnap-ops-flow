"""
Sales Activation Flow — main happy path: qualified lead → trial activated.

Trigger: qualified_lead_wants_trial_or_paid
Steps:
1. sales_triage crew scores the lead
2. deterministic: create pending_signup + checkout session
3. deterministic: send checkout link
4. (checkout completion is handled by Stripe webhook → payment_handler)
5. on checkout complete: run_stage1, then run_stage2 if valid
6. onboarding_handler.start_onboarding
7. update campaign health metrics
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from crewai.flow.flow import Flow, listen, start

from ..adapters.posthog_client import capture as ph_capture
from ..config import settings, thresholds
from ..deterministic.onboarding_handler import OnboardingHandler
from ..deterministic.payment_handler import PaymentHandler, PaymentMethodMissingError
from ..deterministic.provisioning_handler import ProvisioningHandler, pause_stage2
from ..deterministic.retry_handler import RetryCappedError, attempt_retry
from ..deterministic.signup_handler import DuplicatePendingSignupError, SignupHandler
from ..state import OpsFlowState, PendingSignupStatus

logger = logging.getLogger(__name__)


class SalesActivationFlow(Flow[OpsFlowState]):
    """
    Happy path flow: Vapi qualified lead → checkout → provisioned → activated.
    Uses deterministic services for all transactional steps.
    Uses CrewAI (sales_triage crew) only for lead scoring.
    """

    @start()
    def triage_lead(self) -> OpsFlowState:
        """Score the lead with sales_triage crew (cheap model)."""
        event = self.state.event
        if not event:
            self.state.should_abort = True
            return self.state

        lead_data = event.payload
        lead_context = json.dumps(lead_data, indent=2)

        if not settings.is_stub_mode:
            from ..crews.sales_triage.crew import run as triage_run
            result_str = triage_run(lead_context)
            try:
                result = json.loads(result_str)
                self.state.pending_signup.lead_score = result.get("lead_score", 50)
                self.state.pending_signup.is_high_intent = result.get("is_high_intent", False)
                self.state.pending_signup.is_high_fit = result.get("is_high_fit", False)
            except (json.JSONDecodeError, TypeError):
                logger.warning("sales_activation_flow.triage_parse_failed result=%s", result_str[:100])
        else:
            # Stub: assign neutral score
            self.state.pending_signup.lead_score = 60
            self.state.pending_signup.is_high_intent = lead_data.get("expressed_urgency", False)
            self.state.pending_signup.is_high_fit = True

        logger.info(
            "sales_activation_flow.lead_scored score=%s intent=%s fit=%s",
            self.state.pending_signup.lead_score,
            self.state.pending_signup.is_high_intent,
            self.state.pending_signup.is_high_fit,
        )
        entity_id = self.state.event.entity_id if self.state.event else None
        ph_capture(
            entity_id or "ringsnap-ops-flow",
            "ops_lead_scored",
            {
                "lead_score": self.state.pending_signup.lead_score,
                "is_high_intent": self.state.pending_signup.is_high_intent,
                "is_high_fit": self.state.pending_signup.is_high_fit,
                "selected_plan": self.state.pending_signup.selected_plan,
                "trade": self.state.pending_signup.trade,
                "stub_mode": settings.is_stub_mode,
                "environment": settings.environment,
            },
        )
        return self.state

    @listen(triage_lead)
    def create_pending_signup(self) -> OpsFlowState:
        """Create pending_signup record and checkout session."""
        if self.state.should_abort:
            return self.state

        event = self.state.event
        payload = event.payload

        handler = SignupHandler()

        try:
            signup = handler.create_pending_signup(
                contact_name=payload.get("contact_name", ""),
                contact_email=payload.get("contact_email", ""),
                contact_phone=payload.get("contact_phone", ""),
                selected_plan=payload.get("selected_plan", "core"),
                business_name=payload.get("business_name"),
                trade=payload.get("trade"),
                vapi_call_id=event.entity_id,
                lead_score=self.state.pending_signup.lead_score,
                is_high_intent=self.state.pending_signup.is_high_intent,
                is_high_fit=self.state.pending_signup.is_high_fit,
                lead_data=payload,
            )
            self.state.pending_signup = signup

        except DuplicatePendingSignupError as e:
            logger.info(
                "sales_activation_flow.duplicate_signup existing_id=%s email=%s",
                e.existing_id,
                e.email,
            )
            # Update existing record instead of creating new one
            self.state.pending_signup.id = e.existing_id
            self.state.pending_signup.contact_email = e.email

        # Create checkout session
        if self.state.pending_signup.id:
            checkout_url = handler.create_checkout_session(
                pending_signup_id=self.state.pending_signup.id,
                contact_email=self.state.pending_signup.contact_email,
                contact_name=self.state.pending_signup.contact_name,
                selected_plan=self.state.pending_signup.selected_plan,
            )
            self.state.pending_signup.checkout_link = checkout_url

        return self.state

    @listen(create_pending_signup)
    def send_checkout_link(self) -> OpsFlowState:
        """Send checkout link via SMS + email while on the call."""
        if self.state.should_abort or not self.state.pending_signup.id:
            return self.state

        handler = SignupHandler()
        sent = handler.send_checkout_link(
            pending_signup_id=self.state.pending_signup.id,
            contact_phone=self.state.pending_signup.contact_phone,
            contact_email=self.state.pending_signup.contact_email,
            checkout_url=self.state.pending_signup.checkout_link or "",
            contact_name=self.state.pending_signup.contact_name,
            channel="sms+email",
        )

        if sent:
            self.state.pending_signup.status = PendingSignupStatus.LINK_SENT
            logger.info(
                "sales_activation_flow.link_sent id=%s",
                self.state.pending_signup.id,
            )
            ph_capture(
                self.state.pending_signup.id or "ringsnap-ops-flow",
                "ops_checkout_link_sent",
                {
                    "pending_signup_id": self.state.pending_signup.id,
                    "selected_plan": self.state.pending_signup.selected_plan,
                    "lead_score": self.state.pending_signup.lead_score,
                    "is_high_intent": self.state.pending_signup.is_high_intent,
                    "channel": "sms+email",
                    "environment": settings.environment,
                },
            )
        else:
            logger.error(
                "sales_activation_flow.link_send_failed id=%s",
                self.state.pending_signup.id,
            )
            ph_capture(
                self.state.pending_signup.id or "ringsnap-ops-flow",
                "ops_checkout_link_failed",
                {
                    "pending_signup_id": self.state.pending_signup.id,
                    "selected_plan": self.state.pending_signup.selected_plan,
                    "environment": settings.environment,
                },
            )
            self.state.alerts.add(
                severity="warning",  # type: ignore
                message=f"Failed to send checkout link for pending_signup {self.state.pending_signup.id}",
                module="sales_activation_flow",
                entity_id=self.state.pending_signup.id,
            )

        return self.state

    def handle_checkout_completed(self, stripe_session_id: str, account_id: str) -> OpsFlowState:
        """
        Called externally when Stripe webhook fires checkout.session.completed.
        Runs Stage 1 provisioning immediately, Stage 2 after validation.
        """
        payment_handler = PaymentHandler()
        provisioning_handler = ProvisioningHandler()
        onboarding_handler = OnboardingHandler()

        # Update pending signup status
        SignupHandler().handle_checkout_completed(stripe_session_id)

        # Verify PM on file
        pm_context = payment_handler.handle_checkout_completed(stripe_session_id)
        has_pm = pm_context.get("payment_method_captured", False)

        # Stage 1 — always safe after checkout
        pending_id = self.state.pending_signup.id or ""
        stage1_ok = False
        try:
            stage1_ok = attempt_retry(
                fn=lambda: provisioning_handler.run_stage1(account_id, pending_id),
                entity_id=account_id,
                step="stage1",
            ).value
        except RetryCappedError as e:
            logger.error("sales_activation_flow.stage1_retry_cap account_id=%s", account_id)
            provisioning_handler.mark_for_manual_review(account_id, "stage1_retry_capped")
            return self.state

        if not stage1_ok:
            logger.error("sales_activation_flow.stage1_failed account_id=%s", account_id)
            return self.state

        self.state.provisioning.stage1_done = True

        # Stage 2 — only after validation
        validation = provisioning_handler.validate_before_stage2(account_id, has_pm)
        if not validation.is_valid:
            logger.warning(
                "sales_activation_flow.stage2_blocked account_id=%s errors=%s",
                account_id,
                validation.errors,
            )
            for err in validation.errors:
                if "payment_method" in err:
                    pause_stage2(reason=err)
            return self.state

        stage2_ok = False
        try:
            stage2_ok = attempt_retry(
                fn=lambda: provisioning_handler.run_stage2(account_id),
                entity_id=account_id,
                step="stage2",
            ).value
        except RetryCappedError:
            provisioning_handler.mark_for_manual_review(account_id, "stage2_retry_capped")
            return self.state

        if stage2_ok:
            self.state.provisioning.stage2_done = True
            onboarding_state = onboarding_handler.start_onboarding(account_id)
            self.state.onboarding = onboarding_state
            self.state.pending_signup.status = PendingSignupStatus.ACTIVATED
            logger.info("sales_activation_flow.activated account_id=%s", account_id)
            ph_capture(
                account_id or "ringsnap-ops-flow",
                "ops_account_activated",
                {
                    "account_id": account_id,
                    "stripe_session_id": stripe_session_id,
                    "selected_plan": self.state.pending_signup.selected_plan,
                    "lead_score": self.state.pending_signup.lead_score,
                    "environment": settings.environment,
                },
            )

        return self.state
