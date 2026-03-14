"""Tests for adapter stubs — verify they operate correctly in stub mode."""

import pytest


def test_supabase_adapter_stub_query_returns_empty():
    from ringsnap_ops_flow.adapters.supabase_adapter import SupabaseAdapter
    adapter = SupabaseAdapter()
    assert adapter.is_stub is True
    result = adapter.query("accounts")
    assert isinstance(result, list)
    assert len(result) == 0


def test_supabase_adapter_stub_upsert_returns_data():
    from ringsnap_ops_flow.adapters.supabase_adapter import SupabaseAdapter
    adapter = SupabaseAdapter()
    data = {"id": "test_123", "name": "Test"}
    result = adapter.upsert("accounts", data)
    assert result == data


def test_stripe_adapter_stub_checkout():
    from ringsnap_ops_flow.adapters.stripe_adapter import StripeAdapter
    adapter = StripeAdapter()
    assert adapter.is_stub is True
    url = adapter.create_checkout_session({"email": "test@example.com"}, "core", 14)
    assert "stripe" in url.lower() or "checkout" in url.lower()


def test_stripe_adapter_stub_list_pm():
    from ringsnap_ops_flow.adapters.stripe_adapter import StripeAdapter
    adapter = StripeAdapter()
    pms = adapter.list_payment_methods("cus_test_001")
    assert len(pms) >= 1  # Stub returns at least one PM


def test_twilio_adapter_stub_sms():
    from ringsnap_ops_flow.adapters.twilio_adapter import TwilioAdapter
    adapter = TwilioAdapter()
    assert adapter.is_stub is True
    result = adapter.send_sms("+15555550101", "Test message")
    assert result is True


def test_crm_adapter_stub():
    from ringsnap_ops_flow.adapters.crm_adapter import CrmAdapter
    adapter = CrmAdapter()
    assert adapter.is_stub is True
    contact_id = adapter.upsert_contact({"email": "test@example.com"})
    assert contact_id is not None
    task_id = adapter.create_task({"title": "Follow up"})
    assert task_id is not None


def test_support_adapter_stub():
    from ringsnap_ops_flow.adapters.support_adapter import SupportAdapter
    adapter = SupportAdapter()
    assert adapter.is_stub is True
    tickets = adapter.get_unread_tickets()
    assert isinstance(tickets, list)
    assert len(tickets) >= 1
