"""Shared test fixtures for ringsnap_ops_flow tests."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def stub_supabase():
    """Stub Supabase adapter that returns empty results."""
    from ringsnap_ops_flow.adapters.supabase_adapter import SupabaseAdapter
    return SupabaseAdapter()  # No URL/key = stub mode


@pytest.fixture
def stub_stripe():
    from ringsnap_ops_flow.adapters.stripe_adapter import StripeAdapter
    return StripeAdapter()  # No key = stub mode


@pytest.fixture
def stub_twilio():
    from ringsnap_ops_flow.adapters.twilio_adapter import TwilioAdapter
    return TwilioAdapter()  # No credentials = stub mode


@pytest.fixture
def signup_handler(stub_supabase, stub_stripe, stub_twilio):
    from ringsnap_ops_flow.deterministic.signup_handler import SignupHandler
    return SignupHandler(
        supabase_adapter=stub_supabase,
        stripe_adapter=stub_stripe,
        twilio_adapter=stub_twilio,
    )


@pytest.fixture
def payment_handler(stub_supabase, stub_stripe):
    from ringsnap_ops_flow.deterministic.payment_handler import PaymentHandler
    return PaymentHandler(supabase_adapter=stub_supabase, stripe_adapter=stub_stripe)


@pytest.fixture
def provisioning_handler(stub_supabase):
    from ringsnap_ops_flow.deterministic.provisioning_handler import ProvisioningHandler
    return ProvisioningHandler(supabase_adapter=stub_supabase)


@pytest.fixture
def onboarding_handler(stub_supabase):
    from ringsnap_ops_flow.deterministic.onboarding_handler import OnboardingHandler
    return OnboardingHandler(supabase_adapter=stub_supabase)


@pytest.fixture
def funnel_tracker():
    from ringsnap_ops_flow.deterministic.funnel_tracker import FunnelTracker
    return FunnelTracker()  # No adapter = stub mode


@pytest.fixture
def event_gate():
    from ringsnap_ops_flow.event_gate import EventGate
    gate = EventGate()
    gate.reset_daily_counters()
    return gate


@pytest.fixture
def sample_lead_data():
    return {
        "contact_name": "John Smith",
        "contact_email": "john@smithplumbing.com",
        "contact_phone": "+15555550101",
        "business_name": "Smith Plumbing",
        "trade": "plumbing",
        "selected_plan": "core",
        "expressed_urgency": True,
        "monthly_calls": 80,
    }
