"""Onboarding activation crew agents."""
from crewai import Agent
from ...config import models


def onboarding_coach(llm=None) -> Agent:
    return Agent(
        role="Onboarding Success Coach",
        goal="Identify stalled onboarding accounts and recommend the most effective re-engagement action",
        backstory=(
            "You help RingSnap customers complete onboarding. When an account stalls, "
            "you determine the last completed step, diagnose why they stalled, and recommend: "
            "reopen_task | send_reminder | recommend_callback | escalate_to_support. "
            "You prefer the lowest-friction action that will get them to their first live call."
        ),
        llm=llm or models.cheap_model,
        verbose=False,
        allow_delegation=False,
    )
