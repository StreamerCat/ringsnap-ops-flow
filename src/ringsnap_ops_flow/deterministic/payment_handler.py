"""
Payment handler — deterministic payment webhook and subscription lifecycle.

Protected functions:
- handle_checkout_completed
- activate_trial
- handle_payment_failure

No LLM calls. All Stripe actions are idempotent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from ..state import PendingSignupStatus

logger = logging.getLogger(__name__)


class PaymentMethodMissingError(Exception):
    """Raised when trying to activate a trial without a payment method on file."""


class PaymentHandler:
    """
    Handles Stripe webhook events and trial activation logic.
    Works in conjunction with the existing stripe-webhook Edge Function.
    """

    def __init__(self, supabase_adapter=None, stripe_adapter=None):
        self._supabase = supabase_adapter
        self._stripe = stripe_adapter

    def handle_checkout_completed(self, session_id: str, session_data: Optional[dict] = None) -> dict[str, Any]:
        """
        Called when stripe checkout.session.completed fires.
        Idempotent — safe to call multiple times for the same session.

        Protected: do not modify without updating golden tests.

        Returns dict with:
          - pending_signup_id
          - customer_id (Stripe)
          - payment_method_captured (bool)
          - subscription_id (if created)
        """
        result = {
            "session_id": session_id,
            "pending_signup_id": None,
            "customer_id": None,
            "payment_method_captured": False,
            "subscription_id": None,
        }

        if self._supabase and not self._supabase.is_stub:
            rows = self._supabase.query(
                "pending_signups",
                filters={"stripe_checkout_session_id": f"eq.{session_id}"},
            )
            if rows:
                row = rows[0]
                result["pending_signup_id"] = row["id"]

        if self._stripe and not self._stripe.is_stub:
            session = session_data or self._stripe.get_checkout_session(session_id)
            result["customer_id"] = session.get("customer")
            result["payment_method_captured"] = bool(session.get("payment_method_types"))
            result["subscription_id"] = session.get("subscription")
        else:
            # Stub mode
            result["customer_id"] = f"cus_stub_{session_id[:8]}"
            result["payment_method_captured"] = True
            result["subscription_id"] = f"sub_stub_{session_id[:8]}"

        logger.info(
            "payment_handler.checkout_completed session_id=%s pm_captured=%s",
            session_id,
            result["payment_method_captured"],
        )
        return result

    def activate_trial(
        self,
        pending_signup_id: str,
        stripe_customer_id: str,
        plan: str,
        trial_days: int = 14,
    ) -> dict[str, Any]:
        """
        Create or activate the Stripe trial subscription.
        Requires payment method on file — raises PaymentMethodMissingError otherwise.

        Protected: do not activate trials without payment method.

        Returns dict with subscription_id and status.
        """
        # Verify payment method is on file before activating
        if self._stripe and not self._stripe.is_stub:
            pm_list = self._stripe.list_payment_methods(stripe_customer_id)
            if not pm_list:
                raise PaymentMethodMissingError(
                    f"No payment method on file for customer {stripe_customer_id}"
                )
            subscription = self._stripe.create_trial_subscription(
                customer_id=stripe_customer_id,
                plan=plan,
                trial_days=trial_days,
            )
            sub_id = subscription.get("id")
            sub_status = subscription.get("status", "trialing")
        else:
            # Stub mode: simulate successful trial activation
            sub_id = f"sub_trial_stub_{pending_signup_id[:8]}"
            sub_status = "trialing"

        logger.info(
            "payment_handler.trial_activated pending_signup_id=%s sub_id=%s status=%s",
            pending_signup_id,
            sub_id,
            sub_status,
        )

        return {
            "subscription_id": sub_id,
            "status": sub_status,
            "trial_days": trial_days,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }

    def handle_payment_failure(
        self,
        account_id: str,
        invoice_id: str,
        failure_reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Handle Stripe invoice.payment_failed event.
        Logs the failure context for the activation_recovery crew.

        Protected: do not modify retry logic without updating golden tests.
        """
        context = {
            "account_id": account_id,
            "invoice_id": invoice_id,
            "failure_reason": failure_reason or "unknown",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "retry_safe": True,  # Stripe handles payment retries — we only do account-level recovery
        }

        logger.warning(
            "payment_handler.payment_failure account_id=%s invoice_id=%s reason=%s",
            account_id,
            invoice_id,
            failure_reason,
        )

        return context

    def has_payment_method_on_file(self, stripe_customer_id: str) -> bool:
        """
        Check whether a Stripe customer has a valid payment method on file.
        Critical gate before Stage 2 provisioning.
        """
        if self._stripe and not self._stripe.is_stub:
            pm_list = self._stripe.list_payment_methods(stripe_customer_id)
            return len(pm_list) > 0
        # Stub: default to True for testing happy path
        return True
