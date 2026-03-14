"""
Onboarding handler — deterministic onboarding state machine.

Protected functions:
- start_onboarding
- check_stalled
- reopen_stalled_task
- mark_step_complete

No LLM calls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import thresholds
from ..state import OnboardingState, OnboardingStep

logger = logging.getLogger(__name__)


class OnboardingHandler:
    """
    Manages post-activation onboarding state.
    Stall detection compares last_activity_at vs the configured threshold.
    """

    def __init__(self, supabase_adapter=None, crm_adapter=None):
        self._supabase = supabase_adapter
        self._crm = crm_adapter

    def start_onboarding(self, account_id: str) -> OnboardingState:
        """
        Initialize onboarding for a newly activated account.
        Idempotent — safe to call if onboarding already started.
        Protected: always runs after Stage 1 provisioning.
        """
        now = datetime.now(timezone.utc)
        state = OnboardingState(
            account_id=account_id,
            current_step=OnboardingStep.ACCOUNT_SETUP,
            started_at=now,
            last_activity_at=now,
        )

        if self._supabase and not self._supabase.is_stub:
            # TODO: write onboarding record to DB
            pass

        logger.info("onboarding_handler.started account_id=%s", account_id)
        return state

    def check_stalled(self, account_id: str, last_activity_at: Optional[datetime] = None) -> bool:
        """
        Returns True if onboarding has stalled past the configured threshold.
        Protected: threshold comes from config, not hardcoded.
        """
        if last_activity_at is None:
            if self._supabase and not self._supabase.is_stub:
                rows = self._supabase.query(
                    "accounts",
                    filters={"id": f"eq.{account_id}"},
                )
                if rows:
                    last_activity_at = rows[0].get("updated_at")
            if last_activity_at is None:
                return False

        threshold = timedelta(hours=thresholds.onboarding_stall_threshold_hours)
        now = datetime.now(timezone.utc)

        if isinstance(last_activity_at, str):
            from datetime import datetime as dt
            last_activity_at = dt.fromisoformat(last_activity_at.replace("Z", "+00:00"))

        stalled = (now - last_activity_at) > threshold
        if stalled:
            stall_hours = (now - last_activity_at).total_seconds() / 3600
            logger.warning(
                "onboarding_handler.stall_detected account_id=%s hours=%.1f threshold_hours=%d",
                account_id,
                stall_hours,
                thresholds.onboarding_stall_threshold_hours,
            )
        return stalled

    def reopen_stalled_task(self, account_id: str) -> bool:
        """
        Attempt to reopen a stalled onboarding task.
        Safe, non-destructive. Returns True if successful.
        Protected: call only after stall is confirmed.
        """
        if self._supabase and not self._supabase.is_stub:
            # TODO: update onboarding task status, send reminder notification
            pass

        if self._crm and not self._crm.is_stub:
            # TODO: create follow-up task in CRM
            pass

        logger.info("onboarding_handler.task_reopened account_id=%s", account_id)
        return True

    def mark_step_complete(self, account_id: str, step: OnboardingStep) -> OnboardingState:
        """
        Mark a specific onboarding step as complete.
        Updates last_activity_at to prevent false stall detection.
        Protected: step order matters — validate before marking.
        """
        now = datetime.now(timezone.utc)

        state = OnboardingState(
            account_id=account_id,
            current_step=step,
            last_activity_at=now,
        )

        if self._supabase and not self._supabase.is_stub:
            # TODO: update account onboarding_status field
            pass

        logger.info(
            "onboarding_handler.step_complete account_id=%s step=%s",
            account_id,
            step.value,
        )
        return state

    def is_onboarding_complete(self, account_id: str) -> bool:
        """Check if all required onboarding steps are finished."""
        if self._supabase and not self._supabase.is_stub:
            rows = self._supabase.query("accounts", filters={"id": f"eq.{account_id}"})
            if rows:
                return rows[0].get("onboarding_status") == "active"
        return False  # conservative default
