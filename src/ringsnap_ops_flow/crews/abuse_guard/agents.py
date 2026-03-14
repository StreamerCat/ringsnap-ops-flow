"""Abuse guard crew agents."""
from crewai import Agent
from ...config import models


def abuse_analyst(llm=None) -> Agent:
    return Agent(
        role="Abuse & Risk Analyst",
        goal="Detect and respond to abuse patterns, fraud signals, and risk spikes",
        backstory=(
            "You analyze RingSnap abuse signals: trial abuse, fake signups, phone number spam, "
            "excessive call volume, and billing fraud patterns. "
            "You recommend: block_account | flag_for_review | throttle_calls | alert_founder. "
            "You never take irreversible actions automatically — you recommend for human approval."
        ),
        llm=llm or models.default_model,  # Use default model — abuse decisions are higher stakes
        verbose=False,
        allow_delegation=False,
    )
