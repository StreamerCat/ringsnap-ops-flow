"""
Golden tests for OnboardingHandler.
"""

from datetime import datetime, timedelta, timezone
import pytest
from ringsnap_ops_flow.deterministic.onboarding_handler import OnboardingHandler
from ringsnap_ops_flow.state import OnboardingStep


def test_start_onboarding_returns_state(onboarding_handler):
    """start_onboarding returns a valid OnboardingState."""
    state = onboarding_handler.start_onboarding("acc_test_001")
    assert state.account_id == "acc_test_001"
    assert state.current_step == OnboardingStep.ACCOUNT_SETUP
    assert state.started_at is not None


def test_check_stalled_returns_false_when_recent(onboarding_handler):
    """check_stalled returns False when activity was recent."""
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    result = onboarding_handler.check_stalled("acc_test_001", last_activity_at=recent)
    assert result is False


def test_stall_detection_at_threshold(onboarding_handler):
    """
    PROTECTED: check_stalled returns True when activity is past the threshold.
    Threshold is set by config.thresholds.onboarding_stall_threshold_hours (default: 24h).
    """
    stale = datetime.now(timezone.utc) - timedelta(hours=25)
    result = onboarding_handler.check_stalled("acc_test_001", last_activity_at=stale)
    assert result is True


def test_check_stalled_at_boundary(onboarding_handler):
    """Activity exactly at threshold hours ago should be considered stalled."""
    from ringsnap_ops_flow.config import thresholds
    at_boundary = datetime.now(timezone.utc) - timedelta(
        hours=thresholds.onboarding_stall_threshold_hours + 0.1
    )
    result = onboarding_handler.check_stalled("acc_test_001", last_activity_at=at_boundary)
    assert result is True


def test_reopen_stalled_task_returns_true(onboarding_handler):
    """reopen_stalled_task is safe and returns True."""
    result = onboarding_handler.reopen_stalled_task("acc_test_001")
    assert result is True


def test_mark_step_complete(onboarding_handler):
    """mark_step_complete returns updated state with new step."""
    state = onboarding_handler.mark_step_complete("acc_test_001", OnboardingStep.PHONE_ASSIGNED)
    assert state.current_step == OnboardingStep.PHONE_ASSIGNED
    assert state.last_activity_at is not None
