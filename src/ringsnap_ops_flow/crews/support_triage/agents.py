"""Support triage crew agents."""

from ...config import models
from ..repo_awareness import build_agent


def support_triager(llm=None):
    return build_agent(
        role="Support Ticket Triager",
        goal="Classify batched support tickets by priority and category, flag urgent ones",
        backstory=(
            "You triage support tickets for RingSnap, a phone AI for trades businesses. "
            "You classify tickets into: billing | technical | onboarding | feature_request | other. "
            "You flag tickets requiring immediate escalation (e.g. phone down, billing fraud, data issues). "
            "You process tickets in batches, not one at a time."
        ),
        llm=llm or models.cheap_model,
        enable_repo_read=True,
    )
