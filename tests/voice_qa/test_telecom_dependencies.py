"""
Telecom dependency check scaffold.
These tests verify that telecom resource management logic is correctly gated.
"""

import pytest
from unittest.mock import MagicMock, patch


def test_phone_pool_check_returns_bool():
    """Phone pool availability check should return a boolean."""
    from ringsnap_ops_flow.deterministic.provisioning_handler import ProvisioningHandler
    handler = ProvisioningHandler()
    # In stub mode, _has_available_phone_numbers returns True
    result = handler._has_available_phone_numbers()
    assert isinstance(result, bool)


def test_twilio_adapter_stub_number_check():
    """Twilio adapter check_number_availability returns list in stub mode."""
    from ringsnap_ops_flow.adapters.twilio_adapter import TwilioAdapter
    adapter = TwilioAdapter()
    numbers = adapter.check_number_availability("303")
    assert isinstance(numbers, list)
    assert all(n.startswith("+1") for n in numbers)


def test_vapi_adapter_get_call_details_stub():
    """Vapi adapter returns stub call details without real credentials."""
    import asyncio
    from ringsnap_ops_flow.adapters.vapi_adapter import VapiAdapter
    adapter = VapiAdapter()
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(adapter.get_call_details("call_stub_001"))
    loop.close()
    assert result is not None
    assert "id" in result
    assert result["status"] == "completed"


def test_provisioning_validation_blocks_no_phone_pool():
    """
    PROTECTED: provisioning should block if no phone numbers are available.
    """
    from ringsnap_ops_flow.deterministic.provisioning_handler import ProvisioningHandler
    handler = ProvisioningHandler()

    with patch.object(handler, "_has_available_phone_numbers", return_value=False):
        validation = handler.validate_before_stage2("acc_test", has_payment_method=True)
        assert not validation.is_valid
        assert any("phone" in err for err in validation.errors)


def test_stage2_assignment_returns_number_format():
    """Phone number assigned in Stage 2 should be in E.164 format."""
    from ringsnap_ops_flow.deterministic.provisioning_handler import ProvisioningHandler
    handler = ProvisioningHandler()
    # In stub mode, _assign_phone_number returns a stub number
    number = handler._assign_phone_number("acc_test_001")
    assert number is not None
    assert number.startswith("+")
    assert len(number) >= 10
