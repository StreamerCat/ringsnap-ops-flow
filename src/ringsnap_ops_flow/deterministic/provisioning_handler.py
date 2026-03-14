"""
Provisioning handler — two-stage account provisioning.

Stage 1 (lightweight, immediate after checkout):
  - Account shell creation
  - CRM record creation
  - Onboarding state initialization
  - Internal mappings

Stage 2 (COGS-heavy, only after PM confirmed and validation passes):
  - Telecom resource assignment (phone number from pool)
  - Vapi assistant provisioning
  - Other expensive resource allocation

Protected functions:
- run_stage1
- run_stage2
- validate_before_stage2

No LLM calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Global flag — can be set by activation_recovery crew or cost_cogs_monitor
_STAGE2_GLOBALLY_PAUSED: bool = False


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


class ProvisioningHandler:
    """
    Handles account provisioning in two distinct stages.
    Stage 2 is blocked until: checkout completed, PM on file, Stage 1 done, validation passes.
    """

    def __init__(self, supabase_adapter=None, crm_adapter=None, twilio_adapter=None, vapi_adapter=None):
        self._supabase = supabase_adapter
        self._crm = crm_adapter
        self._twilio = twilio_adapter
        self._vapi = vapi_adapter

    # ------------------------------------------------------------------
    # Stage 1 — Lightweight (immediate)
    # ------------------------------------------------------------------

    def run_stage1(self, account_id: str, pending_signup_id: str) -> bool:
        """
        Run Stage 1 provisioning. Safe to retry.
        Protected: do not change what's included in Stage 1 without review.

        Returns True on success, False on failure.
        """
        logger.info("provisioning_handler.stage1_start account_id=%s", account_id)

        steps_completed = []
        try:
            # Step 1: Ensure account shell exists (idempotent upsert)
            self._ensure_account_shell(account_id, pending_signup_id)
            steps_completed.append("account_shell")

            # Step 2: Create CRM record
            self._create_crm_record(account_id)
            steps_completed.append("crm_record")

            # Step 3: Initialize onboarding state
            self._init_onboarding_state(account_id)
            steps_completed.append("onboarding_state")

            # Step 4: Create internal mappings
            self._create_internal_mappings(account_id)
            steps_completed.append("internal_mappings")

            logger.info(
                "provisioning_handler.stage1_complete account_id=%s steps=%s",
                account_id,
                steps_completed,
            )
            return True

        except Exception as e:
            logger.error(
                "provisioning_handler.stage1_failed account_id=%s completed_steps=%s error=%s",
                account_id,
                steps_completed,
                e,
            )
            return False

    # ------------------------------------------------------------------
    # Stage 2 — Expensive (only after PM confirmed)
    # ------------------------------------------------------------------

    def validate_before_stage2(self, account_id: str, has_payment_method: bool) -> ValidationResult:
        """
        Pre-flight validation checks before running Stage 2.
        Protected: gate must not be bypassed.
        """
        result = ValidationResult(is_valid=True)

        if is_stage2_paused():
            result.add_error("stage2_globally_paused")
            return result

        if not has_payment_method:
            result.add_error("no_payment_method_on_file")

        if not self._is_stage1_complete(account_id):
            result.add_error("stage1_not_complete")

        if self._is_already_provisioned(account_id):
            result.add_warning("already_provisioned_idempotent")
            # Not an error — idempotent

        # Check phone pool availability
        if not self._has_available_phone_numbers():
            result.add_error("no_phone_numbers_in_pool")

        return result

    def run_stage2(self, account_id: str) -> bool:
        """
        Run Stage 2 provisioning. Only call after validate_before_stage2 passes.
        Protected: do not bypass validation. Do not run before Stage 1.

        Returns True on success, False on failure (caller should alert + mark for review).
        """
        logger.info("provisioning_handler.stage2_start account_id=%s", account_id)

        steps_completed = []
        try:
            # Step 1: Assign phone number from pool
            phone_number = self._assign_phone_number(account_id)
            if not phone_number:
                raise ValueError("No phone number available from pool")
            steps_completed.append("phone_assigned")

            # Step 2: Provision Vapi assistant
            assistant_id = self._provision_vapi_assistant(account_id)
            steps_completed.append("vapi_assistant")

            # Step 3: Link phone to assistant
            self._link_phone_to_assistant(account_id, phone_number, assistant_id)
            steps_completed.append("phone_linked")

            logger.info(
                "provisioning_handler.stage2_complete account_id=%s steps=%s",
                account_id,
                steps_completed,
            )
            return True

        except Exception as e:
            logger.error(
                "provisioning_handler.stage2_failed account_id=%s completed_steps=%s error=%s",
                account_id,
                steps_completed,
                e,
            )
            return False

    def mark_for_manual_review(self, account_id: str, reason: str) -> bool:
        """
        Mark account for manual review. Safe to call multiple times.
        Protected: only call after automated recovery has failed.
        """
        logger.warning(
            "provisioning_handler.marked_for_manual_review account_id=%s reason=%s",
            account_id,
            reason,
        )
        if self._supabase and not self._supabase.is_stub:
            # TODO: update accounts table or create a manual review task
            pass
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_account_shell(self, account_id: str, pending_signup_id: str) -> None:
        if self._supabase and not self._supabase.is_stub:
            # TODO: verify account exists, update signup_channel = 'sales_guided'
            pass
        logger.debug("provisioning_handler._ensure_account_shell account_id=%s", account_id)

    def _create_crm_record(self, account_id: str) -> None:
        if self._crm and not self._crm.is_stub:
            # TODO: upsert CRM contact
            pass
        logger.debug("provisioning_handler._create_crm_record account_id=%s", account_id)

    def _init_onboarding_state(self, account_id: str) -> None:
        if self._supabase and not self._supabase.is_stub:
            # TODO: initialize onboarding tracking record
            pass
        logger.debug("provisioning_handler._init_onboarding_state account_id=%s", account_id)

    def _create_internal_mappings(self, account_id: str) -> None:
        logger.debug("provisioning_handler._create_internal_mappings account_id=%s", account_id)

    def _assign_phone_number(self, account_id: str) -> Optional[str]:
        if self._supabase and not self._supabase.is_stub:
            # TODO: call existing manage-phone-lifecycle Edge Function
            pass
        return "+10000000001"  # stub

    def _provision_vapi_assistant(self, account_id: str) -> str:
        if self._vapi and not self._vapi.is_stub:
            # TODO: call existing vapi provisioning logic
            pass
        return f"asst_stub_{account_id[:8]}"  # stub

    def _link_phone_to_assistant(self, account_id: str, phone: str, assistant_id: str) -> None:
        logger.debug(
            "provisioning_handler._link_phone account_id=%s phone=%s asst=%s",
            account_id,
            phone,
            assistant_id,
        )

    def _is_stage1_complete(self, account_id: str) -> bool:
        if self._supabase and not self._supabase.is_stub:
            # TODO: check provisioning_jobs table
            pass
        return True  # stub

    def _is_already_provisioned(self, account_id: str) -> bool:
        if self._supabase and not self._supabase.is_stub:
            # TODO: check phone_numbers table for assigned number
            pass
        return False  # stub

    def _has_available_phone_numbers(self) -> bool:
        if self._supabase and not self._supabase.is_stub:
            # TODO: check phone_numbers WHERE lifecycle_status = 'pool'
            pass
        return True  # stub


# ---------------------------------------------------------------------------
# Global Stage 2 pause flag management
# ---------------------------------------------------------------------------


def is_stage2_paused() -> bool:
    return _STAGE2_GLOBALLY_PAUSED


def pause_stage2(reason: str = "") -> None:
    global _STAGE2_GLOBALLY_PAUSED
    _STAGE2_GLOBALLY_PAUSED = True
    logger.warning("provisioning_handler.stage2_paused_globally reason=%s", reason)


def resume_stage2() -> None:
    global _STAGE2_GLOBALLY_PAUSED
    _STAGE2_GLOBALLY_PAUSED = False
    logger.info("provisioning_handler.stage2_resumed")
