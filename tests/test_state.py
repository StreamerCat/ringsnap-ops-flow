"""Tests for shared state models."""

from datetime import datetime, timezone
import pytest
from ringsnap_ops_flow.state import (
    AlertSeverity,
    AlertState,
    ExecutionCountState,
    OpsEvent,
    OpsEventType,
    OpsFlowState,
    PendingSignupState,
    PendingSignupStatus,
    ProvisioningStage,
    ProvisioningState,
)


def test_ops_flow_state_default_construction():
    state = OpsFlowState()
    assert state.event is None
    assert state.should_abort is False
    assert state.pending_signup.status == PendingSignupStatus.QUALIFIED


def test_ops_event_validates_event_type():
    event = OpsEvent(event_type=OpsEventType.QUALIFIED_LEAD, entity_id="test_123")
    assert event.event_type == OpsEventType.QUALIFIED_LEAD


def test_ops_event_invalid_type_raises():
    with pytest.raises(Exception):
        OpsEvent(event_type="not_a_real_event")


def test_alert_state_add_and_has_critical():
    alerts = AlertState()
    alerts.add(AlertSeverity.WARNING, "test warning", "test_module")
    assert not alerts.has_critical()
    alerts.add(AlertSeverity.CRITICAL, "test critical", "test_module")
    assert alerts.has_critical()
    assert len(alerts.alerts) == 2


def test_execution_count_state_increment():
    counts = ExecutionCountState()
    counts.increment("sales_triage", cost_usd=0.001)
    counts.increment("sales_triage", cost_usd=0.002)
    counts.increment("executive_digest", cost_usd=0.010)
    assert counts.get_count("sales_triage") == 2
    assert counts.get_count("executive_digest") == 1
    assert abs(counts.total_cost_today_usd - 0.013) < 1e-9


def test_pending_signup_state_status_flow():
    signup = PendingSignupState(
        contact_name="Test User",
        contact_email="test@example.com",
        contact_phone="+15555550100",
        selected_plan="core",
    )
    assert signup.status == PendingSignupStatus.QUALIFIED
    signup.status = PendingSignupStatus.LINK_SENT
    assert signup.status == PendingSignupStatus.LINK_SENT


def test_provisioning_state_defaults():
    prov = ProvisioningState()
    assert prov.stage == ProvisioningStage.NOT_STARTED
    assert prov.stage1_done is False
    assert prov.stage2_done is False
    assert prov.marked_for_manual_review is False
