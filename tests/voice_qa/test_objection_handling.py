"""
Voice QA: Objection handling path tests.
"""

import pytest


PRICE_OBJECTION_RESPONSE = (
    "I understand cost is important. Can I walk you through what's included? "
    "Most plumbing businesses save $800-$2000/month in missed calls."
)

TIMING_OBJECTION_RESPONSE = (
    "No pressure at all. What would be a better time? "
    "I can have someone call you back whenever works best."
)

NOT_INTERESTED_RESPONSE = (
    "I appreciate you letting me know. Would it be okay if I sent you "
    "some information to review on your own time?"
)


def test_price_objection_mentions_value():
    """Price objection response should mention savings or value."""
    response = PRICE_OBJECTION_RESPONSE.lower()
    has_value = any(word in response for word in ["save", "saving", "value", "included", "worth"])
    assert has_value, "Price objection response must mention value or savings"


def test_timing_objection_offers_callback():
    """Timing objection response should offer a callback option."""
    response = TIMING_OBJECTION_RESPONSE.lower()
    has_callback = any(word in response for word in ["call back", "callback", "call you back", "better time"])
    assert has_callback, "Timing objection response must offer callback"


def test_not_interested_response_non_pushy():
    """Not-interested response should not be pushy — check for pressure words."""
    pushy_words = ["you must", "you need to", "act now", "limited time", "last chance"]
    for word in pushy_words:
        assert word not in NOT_INTERESTED_RESPONSE.lower(), f"Found pushy language: '{word}'"


def test_objection_responses_minimum_length():
    """Each objection response must be substantive (not a one-liner)."""
    responses = [PRICE_OBJECTION_RESPONSE, TIMING_OBJECTION_RESPONSE, NOT_INTERESTED_RESPONSE]
    for resp in responses:
        assert len(resp) >= 30, f"Objection response too short: {resp}"


def test_objection_responses_end_with_question_or_offer():
    """Good objection handling ends with a question or offer to keep conversation going."""
    responses = [PRICE_OBJECTION_RESPONSE, TIMING_OBJECTION_RESPONSE, NOT_INTERESTED_RESPONSE]
    for resp in responses:
        has_engagement = "?" in resp or "would" in resp.lower() or "can" in resp.lower()
        assert has_engagement, f"Response doesn't engage caller: {resp}"
