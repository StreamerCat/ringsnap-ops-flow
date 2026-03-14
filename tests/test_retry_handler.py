"""
Golden tests for retry_handler — protected retry logic.
"""

import pytest
from ringsnap_ops_flow.deterministic.retry_handler import (
    RetryCappedError,
    attempt_retry,
    is_retry_capped,
)


def test_attempt_retry_success_on_first_try():
    """attempt_retry returns success when fn succeeds immediately."""
    result = attempt_retry(fn=lambda: 42, entity_id="acc_001", step="test_step")
    assert result.success is True
    assert result.value == 42
    assert result.attempts == 1


def test_attempt_retry_succeeds_after_failure():
    """attempt_retry retries on failure and succeeds eventually."""
    call_count = [0]

    def flaky_fn():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ValueError("temporary failure")
        return "ok"

    result = attempt_retry(
        fn=flaky_fn,
        entity_id="acc_001",
        step="flaky_step",
        wait_min=0.01,
        wait_max=0.05,
    )
    assert result.success is True
    assert result.value == "ok"
    assert result.attempts >= 2


def test_retry_cap_raises_after_max_attempts():
    """
    PROTECTED: attempt_retry raises RetryCappedError when all attempts fail.
    Callers must catch this and alert — not loop.
    """
    def always_fails():
        raise ValueError("always fails")

    with pytest.raises(RetryCappedError) as exc_info:
        attempt_retry(
            fn=always_fails,
            entity_id="acc_cap_test",
            step="always_failing_step",
            max_attempts=2,
            wait_min=0.01,
            wait_max=0.05,
        )

    assert exc_info.value.entity_id == "acc_cap_test"
    assert exc_info.value.step == "always_failing_step"
    assert "always fails" in exc_info.value.last_error


def test_is_retry_capped_below_limit():
    assert is_retry_capped(current_attempts=2, max_attempts=3) is False


def test_is_retry_capped_at_limit():
    assert is_retry_capped(current_attempts=3, max_attempts=3) is True


def test_is_retry_capped_above_limit():
    assert is_retry_capped(current_attempts=5, max_attempts=3) is True
