"""
Signup handler — deterministic pending_signup lifecycle management.

Protected functions (must not change behavior without golden test updates):
- create_pending_signup
- create_checkout_session
- send_checkout_link
- expire_stale_pending_signups

No LLM calls.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import thresholds
from ..state import PendingSignupState, PendingSignupStatus

logger = logging.getLogger(__name__)


class DuplicatePendingSignupError(Exception):
    """Raised when a non-terminal pending signup already exists for this contact."""

    def __init__(self, existing_id: str, email: str):
        self.existing_id = existing_id
        self.email = email
        super().__init__(f"Active pending signup already exists for {email}: {existing_id}")


class SignupHandler:
    """
    Manages the pending_signup lifecycle for the phone sales hybrid checkout flow.
    All methods are idempotent where possible.
    """

    def __init__(self, supabase_adapter=None, stripe_adapter=None, twilio_adapter=None, resend_adapter=None):
        self._supabase = supabase_adapter
        self._stripe = stripe_adapter
        self._twilio = twilio_adapter
        self._resend = resend_adapter

    def create_pending_signup(
        self,
        contact_name: str,
        contact_email: str,
        contact_phone: str,
        selected_plan: str,
        business_name: Optional[str] = None,
        trade: Optional[str] = None,
        vapi_call_id: Optional[str] = None,
        sales_rep_id: Optional[str] = None,
        lead_score: Optional[int] = None,
        is_high_intent: bool = False,
        is_high_fit: bool = False,
        lead_data: Optional[dict] = None,
    ) -> PendingSignupState:
        """
        Create a new pending_signup record.

        Raises DuplicatePendingSignupError if an active (non-terminal) signup
        already exists for this email within the cooldown window.
        """
        # Dedupe check
        existing = self._find_active_by_email(contact_email)
        if existing:
            raise DuplicatePendingSignupError(existing_id=existing["id"], email=contact_email)

        expires_at = datetime.now(timezone.utc) + timedelta(hours=thresholds.pending_signup_expiry_hours)

        record = {
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "selected_plan": selected_plan,
            "business_name": business_name,
            "trade": trade,
            "vapi_call_id": vapi_call_id,
            "sales_rep_id": sales_rep_id,
            "lead_score": lead_score,
            "is_high_intent": is_high_intent,
            "is_high_fit": is_high_fit,
            "lead_data": lead_data or {},
            "expires_at": expires_at.isoformat(),
            "status": PendingSignupStatus.QUALIFIED,
        }

        if self._supabase and not self._supabase.is_stub:
            result = self._supabase.upsert("pending_signups", record)
            record["id"] = result.get("id")
        else:
            # Stub mode: generate a fake ID
            record["id"] = str(uuid.uuid4())

        logger.info(
            "signup_handler.created id=%s email=%s plan=%s",
            record["id"],
            contact_email,
            selected_plan,
        )

        return PendingSignupState(
            id=record["id"],
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            selected_plan=selected_plan,
            business_name=business_name,
            trade=trade,
            status=PendingSignupStatus.QUALIFIED,
            vapi_call_id=vapi_call_id,
            sales_rep_id=sales_rep_id,
            lead_score=lead_score,
            is_high_intent=is_high_intent,
            is_high_fit=is_high_fit,
            lead_data=lead_data or {},
            expires_at=expires_at,
        )

    def create_checkout_session(
        self,
        pending_signup_id: str,
        contact_email: str,
        contact_name: str,
        selected_plan: str,
        trial_days: int = 14,
    ) -> str:
        """
        Create a Stripe Checkout Session and store the link.
        Returns the checkout URL.
        Protected: do not change behavior without updating golden tests.
        """
        if self._stripe and not self._stripe.is_stub:
            # TODO: pass real Stripe price IDs from env
            checkout_url = self._stripe.create_checkout_session(
                customer_data={"email": contact_email, "name": contact_name},
                plan=selected_plan,
                trial_days=trial_days,
                metadata={"pending_signup_id": pending_signup_id},
            )
        else:
            # Stub: return a fake URL for testing
            checkout_url = f"https://checkout.stripe.com/stub/{pending_signup_id}"

        # Persist the link
        self._update_status(
            pending_signup_id,
            PendingSignupStatus.LINK_SENT,
            extra={"checkout_link": checkout_url, "link_sent_at": datetime.now(timezone.utc).isoformat()},
        )

        logger.info(
            "signup_handler.checkout_session_created id=%s plan=%s",
            pending_signup_id,
            selected_plan,
        )
        return checkout_url

    def send_checkout_link(
        self,
        pending_signup_id: str,
        contact_phone: str,
        contact_email: str,
        checkout_url: str,
        contact_name: str = "",
        channel: str = "sms+email",
    ) -> bool:
        """
        Send the secure checkout link via SMS and/or email.
        Protected: do not send to real customers without real credentials.
        """
        sent = False
        message = f"Hi {contact_name or 'there'}! Here's your secure RingSnap signup link: {checkout_url}"

        if "sms" in channel and self._twilio and not self._twilio.is_stub:
            try:
                self._twilio.send_sms(to=contact_phone, body=message)
                sent = True
                logger.info("signup_handler.sms_sent id=%s phone=%s", pending_signup_id, contact_phone)
            except Exception as e:
                logger.error("signup_handler.sms_failed id=%s error=%s", pending_signup_id, e)
        else:
            logger.info("signup_handler.sms_stub id=%s", pending_signup_id)
            sent = True  # stub always succeeds

        if "email" in channel and self._resend and not self._resend.is_stub:
            try:
                self._resend.send_checkout_email(to=contact_email, checkout_url=checkout_url, name=contact_name)
                sent = True
                logger.info("signup_handler.email_sent id=%s email=%s", pending_signup_id, contact_email)
            except Exception as e:
                logger.error("signup_handler.email_failed id=%s error=%s", pending_signup_id, e)

        return sent

    def handle_checkout_completed(self, stripe_session_id: str) -> Optional[PendingSignupState]:
        """
        Idempotent handler called when Stripe checkout.session.completed fires.
        Updates pending_signup status to checkout_completed.
        Protected: this is the critical handoff point.
        """
        if self._supabase and not self._supabase.is_stub:
            rows = self._supabase.query(
                "pending_signups",
                filters={"stripe_checkout_session_id": f"eq.{stripe_session_id}"},
            )
            if not rows:
                logger.warning(
                    "signup_handler.checkout_completed_no_match session_id=%s",
                    stripe_session_id,
                )
                return None
            row = rows[0]
            # Idempotency: if already completed, return existing state
            if row["status"] == PendingSignupStatus.CHECKOUT_COMPLETED:
                logger.info(
                    "signup_handler.checkout_already_completed id=%s",
                    row["id"],
                )
            else:
                self._update_status(
                    row["id"],
                    PendingSignupStatus.CHECKOUT_COMPLETED,
                    extra={"checkout_completed_at": datetime.now(timezone.utc).isoformat()},
                )
            return PendingSignupState(**row)
        else:
            # Stub mode
            logger.info("signup_handler.checkout_completed_stub session_id=%s", stripe_session_id)
            return PendingSignupState(
                id=str(uuid.uuid4()),
                stripe_checkout_session_id=stripe_session_id,
                status=PendingSignupStatus.CHECKOUT_COMPLETED,
                contact_email="stub@example.com",
                contact_name="Stub User",
                contact_phone="+10000000000",
                selected_plan="core",
                checkout_completed_at=datetime.now(timezone.utc),
            )

    def expire_stale_pending_signups(self) -> int:
        """
        Mark expired pending signups. Safe to run repeatedly.
        Returns count of records expired.
        """
        now = datetime.now(timezone.utc)
        if self._supabase and not self._supabase.is_stub:
            # TODO: UPDATE pending_signups SET status='expired'
            # WHERE expires_at < NOW() AND status NOT IN ('activated','expired','failed')
            logger.info("signup_handler.expire_stale_stub")
            return 0
        return 0

    def resend_checkout_link(self, pending_signup_id: str) -> bool:
        """
        Resend the checkout link once. Enforces max_rescue_attempts limit.
        Protected: do not loop, do not send more than once per rescue attempt.
        """
        if self._supabase and not self._supabase.is_stub:
            rows = self._supabase.query("pending_signups", filters={"id": f"eq.{pending_signup_id}"})
            if not rows:
                return False
            row = rows[0]
            attempts = row.get("rescue_attempts", 0)
            from ..config import execution as exec_cfg

            if attempts >= exec_cfg.max_rescue_attempts:
                logger.warning(
                    "signup_handler.rescue_cap_reached id=%s attempts=%d",
                    pending_signup_id,
                    attempts,
                )
                return False
            # Send link
            sent = self.send_checkout_link(
                pending_signup_id=pending_signup_id,
                contact_phone=row["contact_phone"],
                contact_email=row["contact_email"],
                checkout_url=row["checkout_link"],
                contact_name=row["contact_name"],
            )
            if sent:
                self._supabase.upsert(
                    "pending_signups",
                    {"id": pending_signup_id, "rescue_attempts": attempts + 1},
                )
            return sent
        return True  # stub

    def _find_active_by_email(self, email: str) -> Optional[dict]:
        if self._supabase and not self._supabase.is_stub:
            terminal = ["activated", "expired", "failed"]
            rows = self._supabase.query(
                "pending_signups",
                filters={"contact_email": f"eq.{email}"},
            )
            for row in rows:
                if row.get("status") not in terminal:
                    return row
        return None

    def _update_status(self, record_id: str, status: PendingSignupStatus, extra: Optional[dict] = None) -> None:
        if self._supabase and not self._supabase.is_stub:
            update = {"id": record_id, "status": status.value}
            if extra:
                update.update(extra)
            self._supabase.upsert("pending_signups", update)
        logger.info("signup_handler.status_update id=%s status=%s", record_id, status.value)
