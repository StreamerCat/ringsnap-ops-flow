"""
Voice QA: Fallback handling scaffold.
Tests that fallback scripts are defined and non-empty.
"""

import pytest


# Sample fallback configurations — these would come from assistant_templates in production
SAMPLE_ASSISTANT_CONFIG = {
    "fallback_script": "I'm sorry, I didn't catch that. Could you repeat that for me?",
    "tool_failure_fallback": "I'm having a technical issue. Let me take your info and have {owner_name} call you back.",
    "silence_handler": "Are you still there? I want to make sure I can help you today.",
    "end_of_call": "Thank you for calling {company_name}. We'll be in touch shortly!",
    "objection_handling": {
        "price": "I understand cost is important. Can I walk you through what's included and what other businesses like yours typically save?",
        "timing": "No pressure at all. What would be a better time? I can call back whenever works for you.",
        "not_interested": "I appreciate you letting me know. Would it be okay if I send you some information you can review on your own time?",
    },
    "booking_confirmation": "Great! I've scheduled your appointment for {appointment_time}. You'll receive a confirmation text shortly.",
}

INCOMPLETE_CONFIG = {
    # Missing fallback_script, silence_handler, objection_handling
    "end_of_call": "Thank you!"
}


def test_fallback_script_exists():
    """PROTECTED: fallback_script must exist and be non-empty."""
    assert "fallback_script" in SAMPLE_ASSISTANT_CONFIG
    assert len(SAMPLE_ASSISTANT_CONFIG["fallback_script"]) > 10


def test_tool_failure_fallback_exists():
    """tool_failure_fallback must handle cases where Vapi tool calls fail."""
    assert "tool_failure_fallback" in SAMPLE_ASSISTANT_CONFIG
    assert len(SAMPLE_ASSISTANT_CONFIG["tool_failure_fallback"]) > 10


def test_silence_handler_exists():
    """Silence handler must be configured to prevent dead air."""
    assert "silence_handler" in SAMPLE_ASSISTANT_CONFIG
    assert len(SAMPLE_ASSISTANT_CONFIG["silence_handler"]) > 5


def test_objection_handling_present():
    """PROTECTED: objection_handling must cover price, timing, and not_interested."""
    required_objections = ["price", "timing", "not_interested"]
    handling = SAMPLE_ASSISTANT_CONFIG.get("objection_handling", {})
    for objection in required_objections:
        assert objection in handling, f"Missing objection handler for: {objection}"
        assert len(handling[objection]) > 20, f"Handler too short for: {objection}"


def test_booking_confirmation_exists():
    """Booking confirmation script must exist when booking mode is enabled."""
    assert "booking_confirmation" in SAMPLE_ASSISTANT_CONFIG
    assert len(SAMPLE_ASSISTANT_CONFIG["booking_confirmation"]) > 10


def test_incomplete_config_detected():
    """Incomplete config should fail fallback checks."""
    missing_fields = []
    required = ["fallback_script", "silence_handler", "objection_handling", "booking_confirmation"]
    for field in required:
        if field not in INCOMPLETE_CONFIG or not INCOMPLETE_CONFIG.get(field):
            missing_fields.append(field)
    assert len(missing_fields) > 0, "Incomplete config should have been detected"
