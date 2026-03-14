"""
Golden tests for ProvisioningHandler — protected two-stage provisioning logic.
Do not change behavior without updating these tests.
"""

import pytest
from unittest.mock import MagicMock, patch

from ringsnap_ops_flow.deterministic.provisioning_handler import (
    ProvisioningHandler,
    pause_stage2,
    resume_stage2,
    is_stage2_paused,
)


def test_run_stage1_succeeds_in_stub(provisioning_handler):
    """Stage 1 should complete successfully in stub mode."""
    result = provisioning_handler.run_stage1("acc_test_001", "ps_test_001")
    assert result is True


def test_run_stage2_succeeds_in_stub(provisioning_handler):
    """Stage 2 should complete successfully in stub mode."""
    result = provisioning_handler.run_stage2("acc_test_001")
    assert result is True


def test_stage2_blocked_before_stage1():
    """
    PROTECTED: Stage 2 must be blocked when Stage 1 is not complete.
    """
    handler = ProvisioningHandler()

    with patch.object(handler, "_is_stage1_complete", return_value=False):
        validation = handler.validate_before_stage2("acc_test_001", has_payment_method=True)
        assert not validation.is_valid
        assert any("stage1" in err for err in validation.errors)


def test_stage2_blocked_before_checkout_complete():
    """
    PROTECTED: Stage 2 must be blocked when no payment method is on file.
    This is the critical gate preventing expensive provisioning before checkout.
    """
    handler = ProvisioningHandler()
    validation = handler.validate_before_stage2("acc_test_001", has_payment_method=False)
    assert not validation.is_valid
    assert any("payment_method" in err for err in validation.errors)


def test_stage2_blocked_when_globally_paused():
    """Stage 2 must be blocked when the global pause flag is set."""
    resume_stage2()  # ensure clean state
    assert not is_stage2_paused()

    pause_stage2(reason="test_pause")
    assert is_stage2_paused()

    handler = ProvisioningHandler()
    validation = handler.validate_before_stage2("acc_test_001", has_payment_method=True)
    assert not validation.is_valid
    assert any("paused" in err for err in validation.errors)

    resume_stage2()  # cleanup
    assert not is_stage2_paused()


def test_stage2_passes_all_checks():
    """Stage 2 validation passes when all conditions are met in stub mode."""
    handler = ProvisioningHandler()
    validation = handler.validate_before_stage2("acc_test_valid", has_payment_method=True)
    # In stub mode, all checks should pass (no DB, stage1 always returns True)
    assert validation.is_valid


def test_mark_for_manual_review_does_not_raise(provisioning_handler):
    """mark_for_manual_review is always safe to call."""
    result = provisioning_handler.mark_for_manual_review("acc_test_001", "test_reason")
    assert result is True
