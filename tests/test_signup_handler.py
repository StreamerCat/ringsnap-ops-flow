"""
Golden tests for SignupHandler — protected functions.
Do not change behavior without updating these tests.
"""

import pytest
from unittest.mock import MagicMock, patch

from ringsnap_ops_flow.deterministic.signup_handler import (
    DuplicatePendingSignupError,
    SignupHandler,
)
from ringsnap_ops_flow.state import PendingSignupStatus


def test_create_pending_signup_happy_path(signup_handler, sample_lead_data):
    """Creating a pending signup returns a valid PendingSignupState."""
    signup = signup_handler.create_pending_signup(
        contact_name=sample_lead_data["contact_name"],
        contact_email=sample_lead_data["contact_email"],
        contact_phone=sample_lead_data["contact_phone"],
        selected_plan=sample_lead_data["selected_plan"],
        business_name=sample_lead_data["business_name"],
        trade=sample_lead_data["trade"],
    )
    assert signup.id is not None
    assert signup.contact_email == sample_lead_data["contact_email"]
    assert signup.status == PendingSignupStatus.QUALIFIED
    assert signup.expires_at is not None


def test_create_pending_signup_has_expiry(signup_handler, sample_lead_data):
    """Pending signups must always have an expiry time set."""
    signup = signup_handler.create_pending_signup(
        contact_name="Test",
        contact_email="test@example.com",
        contact_phone="+15555550101",
        selected_plan="lite",
    )
    assert signup.expires_at is not None


def test_create_pending_signup_dedupe_blocks_duplicate(signup_handler, sample_lead_data):
    """
    PROTECTED: Duplicate pending signup for same email raises DuplicatePendingSignupError.
    This prevents double-provisioning and double-checkout for the same contact.
    """
    # Simulate existing active record by mocking _find_active_by_email
    with patch.object(
        signup_handler,
        "_find_active_by_email",
        return_value={"id": "existing_id_123"},
    ):
        with pytest.raises(DuplicatePendingSignupError) as exc_info:
            signup_handler.create_pending_signup(
                contact_name=sample_lead_data["contact_name"],
                contact_email=sample_lead_data["contact_email"],
                contact_phone=sample_lead_data["contact_phone"],
                selected_plan="core",
            )
        assert exc_info.value.existing_id == "existing_id_123"
        assert exc_info.value.email == sample_lead_data["contact_email"]


def test_create_checkout_session_returns_url(signup_handler):
    """create_checkout_session must return a non-empty URL."""
    url = signup_handler.create_checkout_session(
        pending_signup_id="ps_test_123",
        contact_email="buyer@example.com",
        contact_name="Test Buyer",
        selected_plan="core",
    )
    assert url is not None
    assert len(url) > 0
    assert "stripe" in url.lower() or "checkout" in url.lower()


def test_send_checkout_link_stub_succeeds(signup_handler):
    """send_checkout_link returns True in stub mode."""
    result = signup_handler.send_checkout_link(
        pending_signup_id="ps_test_456",
        contact_phone="+15555550101",
        contact_email="buyer@example.com",
        checkout_url="https://checkout.stripe.com/test",
        contact_name="Test",
    )
    assert result is True


def test_handle_checkout_completed_stub_returns_state(signup_handler):
    """handle_checkout_completed in stub mode returns a valid PendingSignupState."""
    state = signup_handler.handle_checkout_completed("cs_test_session_001")
    assert state is not None
    assert state.stripe_checkout_session_id == "cs_test_session_001"
    assert state.status == PendingSignupStatus.CHECKOUT_COMPLETED


def test_handle_checkout_completed_idempotent(signup_handler):
    """handle_checkout_completed should be safe to call multiple times."""
    state1 = signup_handler.handle_checkout_completed("cs_test_idem_001")
    state2 = signup_handler.handle_checkout_completed("cs_test_idem_001")
    assert state1 is not None
    assert state2 is not None
    # Both should return completed status
    assert state1.status == PendingSignupStatus.CHECKOUT_COMPLETED
    assert state2.status == PendingSignupStatus.CHECKOUT_COMPLETED
