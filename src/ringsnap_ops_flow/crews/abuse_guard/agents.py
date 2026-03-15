"""Abuse guard crew agents."""

from ...config import models
from ..repo_awareness import build_agent


def abuse_analyst(llm=None):
    return build_agent(
        role="Abuse & Risk Analyst",
        goal="Detect and respond to abuse patterns, fraud signals, and risk spikes",
        backstory=(
            "You analyze RingSnap abuse signals: trial abuse, fake signups, phone number spam, "
            "excessive call volume, and billing fraud patterns. "
            "You recommend: block_account | flag_for_review | throttle_calls | alert_founder. "
            "You never take irreversible actions automatically — you recommend for human approval."
        ),
        llm=llm or models.default_model,
        enable_repo_read=True,
    )
