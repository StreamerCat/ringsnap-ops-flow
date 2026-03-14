"""Executive digest crew agents."""
from crewai import Agent
from ...config import models


def digest_writer(llm=None) -> Agent:
    return Agent(
        role="Executive Digest Writer",
        goal="Write a concise, actionable daily operational digest for the RingSnap founder",
        backstory=(
            "You write the daily RingSnap ops digest. You receive raw metrics and turn them into "
            "a clear, founder-friendly report. You highlight what needs attention today, "
            "what's working, and what 1-2 actions are most important. "
            "You are honest about problems and concise about successes. "
            "You output markdown, formatted for easy scanning."
        ),
        llm=llm or models.default_model,
        verbose=False,
        allow_delegation=False,
    )
