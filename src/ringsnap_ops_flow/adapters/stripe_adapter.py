"""
Stripe adapter — checkout session creation and subscription management.
# TODO: implement with real Stripe secret key from config
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import BaseAdapter

logger = logging.getLogger(__name__)

# Map plan names to Stripe price ID env var names
PLAN_TO_PRICE_ENV: dict[str, str] = {
    "night_weekend": "STRIPE_PRICE_ID_NIGHT_WEEKEND",
    "lite": "STRIPE_PRICE_ID_LITE",
    "core": "STRIPE_PRICE_ID_CORE",
    "pro": "STRIPE_PRICE_ID_PRO",
}


class StripeAdapter(BaseAdapter):
    """
    Wraps Stripe Python SDK for ops flow checkout and subscription operations.
    Real implementation requires STRIPE_SECRET_KEY.
    """

    def __init__(self, secret_key: str = ""):
        stub = not secret_key or secret_key.startswith("sk_stub")
        super().__init__(stub=stub)
        self._stripe = None
        if not stub:
            try:
                import stripe as stripe_lib
                stripe_lib.api_key = secret_key
                self._stripe = stripe_lib
                logger.info("stripe_adapter.connected")
            except ImportError:
                logger.error("stripe_adapter.import_failed")
                self._stub = True

    def create_checkout_session(
        self,
        customer_data: dict[str, str],
        plan: str,
        trial_days: int = 14,
        success_url: str = "https://app.ringsnap.com/onboarding?session_id={CHECKOUT_SESSION_ID}",
        cancel_url: str = "https://app.ringsnap.com/signup?cancelled=1",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Create a Stripe Checkout Session for the given plan with trial.
        Returns the session URL.
        # TODO: pass real price IDs from environment
        """
        if self.is_stub:
            self._log_stub("create_checkout_session", plan=plan)
            return f"https://checkout.stripe.com/stub/session_{plan}"

        import os
        price_env = PLAN_TO_PRICE_ENV.get(plan.lower(), "STRIPE_PRICE_ID_CORE")
        price_id = os.environ.get(price_env, "")
        if not price_id:
            raise ValueError(f"Stripe price ID not configured for plan '{plan}'. Set {price_env}.")

        session = self._stripe.checkout.Session.create(
            customer_email=customer_data.get("email"),
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            subscription_data={"trial_period_days": trial_days},
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )
        return session.url

    def get_checkout_session(self, session_id: str) -> dict[str, Any]:
        """Retrieve a Checkout Session by ID."""
        if self.is_stub:
            self._log_stub("get_checkout_session", session_id=session_id)
            return {
                "id": session_id,
                "customer": f"cus_stub_{session_id[:8]}",
                "subscription": f"sub_stub_{session_id[:8]}",
                "payment_method_types": ["card"],
            }
        session = self._stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
        return dict(session)

    def list_payment_methods(self, customer_id: str) -> list[dict]:
        """List payment methods for a customer."""
        if self.is_stub:
            self._log_stub("list_payment_methods", customer_id=customer_id)
            return [{"id": "pm_stub_1234", "type": "card"}]

        result = self._stripe.PaymentMethod.list(customer=customer_id, type="card")
        return result.data or []

    def create_trial_subscription(
        self,
        customer_id: str,
        plan: str,
        trial_days: int = 14,
    ) -> dict[str, Any]:
        """Create a trial subscription for an existing customer."""
        if self.is_stub:
            self._log_stub("create_trial_subscription", customer_id=customer_id, plan=plan)
            return {"id": f"sub_stub_{customer_id[:8]}", "status": "trialing"}

        import os
        price_env = PLAN_TO_PRICE_ENV.get(plan.lower(), "STRIPE_PRICE_ID_CORE")
        price_id = os.environ.get(price_env, "")
        sub = self._stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            trial_period_days=trial_days,
        )
        return dict(sub)
