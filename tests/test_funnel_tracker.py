"""Tests for FunnelTracker and FunnelBreakpoints."""

import pytest
from ringsnap_ops_flow.deterministic.funnel_tracker import FunnelBreakpoints, FunnelTracker
from ringsnap_ops_flow.state import PendingSignupStatus


def test_funnel_breakpoints_checkout_completion_rate():
    bp = FunnelBreakpoints({
        PendingSignupStatus.LINK_SENT: 10,
        PendingSignupStatus.CHECKOUT_COMPLETED: 7,
        PendingSignupStatus.ACTIVATED: 6,
    })
    assert abs(bp.checkout_completion_rate - 0.7) < 0.001


def test_funnel_breakpoints_activation_rate():
    bp = FunnelBreakpoints({
        PendingSignupStatus.CHECKOUT_COMPLETED: 10,
        PendingSignupStatus.ACTIVATED: 8,
    })
    assert abs(bp.activation_rate - 0.8) < 0.001


def test_funnel_breakpoints_no_data_returns_healthy():
    """With no data, all rates should default to 1.0 (assume healthy)."""
    bp = FunnelBreakpoints({})
    assert bp.checkout_completion_rate == 1.0
    assert bp.activation_rate == 1.0
    assert not bp.should_activate_safe_mode()


def test_funnel_breakpoints_below_threshold_recommends_safe_mode():
    """If checkout rate is below 0.50 threshold, safe mode should be recommended."""
    bp = FunnelBreakpoints({
        PendingSignupStatus.LINK_SENT: 10,
        PendingSignupStatus.CHECKOUT_COMPLETED: 4,  # 40% < 50% threshold
        PendingSignupStatus.ACTIVATED: 3,
    })
    assert bp.is_checkout_below_threshold()
    assert bp.should_activate_safe_mode()


def test_funnel_tracker_stub_returns_healthy_data(funnel_tracker):
    """FunnelTracker in stub mode returns healthy breakpoints."""
    bp = funnel_tracker.get_breakpoints()
    assert bp.total_started > 0
    assert bp.checkout_completion_rate <= 1.0


def test_funnel_tracker_estimated_waste_prevented(funnel_tracker):
    """estimated_waste_prevented_usd returns a non-negative float."""
    waste = funnel_tracker.estimated_waste_prevented_usd()
    assert isinstance(waste, float)
    assert waste >= 0.0
