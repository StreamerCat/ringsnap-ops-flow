"""
Golden tests for PaymentHandler — protected functions.
Do not change behavior without updating these tests.
"""

import pytest
from ringsnap_ops_flow.deterministic.payment_handler import (
    PaymentHandler,
    PaymentMethodMissingError,
)


def test_handle_checkout_completed_returns_context(payment_handler):
    """PROTECTED: checkout completed handler returns context with PM captured."""
    result = payment_handler.handle_checkout_completed("cs_test_001")
    assert result["session_id"] == "cs_test_001"
    assert result["payment_method_captured"] is True
    assert result["customer_id"] is not None


def test_activate_trial_stub_succeeds(payment_handler):
    """activate_trial returns valid subscription data in stub mode."""
    result = payment_handler.activate_trial(
        pending_signup_id="ps_test_001",
        stripe_customer_id="cus_stub_001",
        plan="core",
        trial_days=14,
    )
    assert result["subscription_id"] is not None
    assert result["status"] == "trialing"
    assert result["trial_days"] == 14


def test_activate_trial_requires_payment_method():
    """
    PROTECTED: activate_trial must raise PaymentMethodMissingError if no PM on file.
    This is the critical guard against free-trial abuse.
    """
    from unittest.mock import MagicMock

    mock_stripe = MagicMock()
    mock_stripe.is_stub = False
    mock_stripe.list_payment_methods = MagicMock(return_value=[])  # Empty = no PM

    handler = PaymentHandler(stripe_adapter=mock_stripe)

    with pytest.raises(PaymentMethodMissingError):
        handler.activate_trial(
            pending_signup_id="ps_no_pm",
            stripe_customer_id="cus_no_pm_001",
            plan="core",
        )


def test_has_payment_method_on_file_stub(payment_handler):
    """has_payment_method_on_file returns True in stub mode (safe default for tests)."""
    result = payment_handler.has_payment_method_on_file("cus_stub_001")
    assert result is True


def test_handle_payment_failure_returns_context(payment_handler):
    """handle_payment_failure returns structured context dict."""
    result = payment_handler.handle_payment_failure(
        account_id="acc_test_001",
        invoice_id="inv_test_001",
        failure_reason="card_declined",
    )
    assert result["account_id"] == "acc_test_001"
    assert result["invoice_id"] == "inv_test_001"
    assert result["failure_reason"] == "card_declined"
    assert result["retry_safe"] is True
    assert "detected_at" in result
