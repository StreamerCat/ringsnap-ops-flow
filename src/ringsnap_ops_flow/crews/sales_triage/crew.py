"""Sales triage crew — scores qualified leads and determines checkout strategy."""

from __future__ import annotations

from crewai import Crew, Process

from ...config import models
from .agents import lead_qualifier
from .tasks import score_lead_task


def build_crew(lead_context: str) -> Crew:
    """
    Trigger: qualified_lead_wants_trial_or_paid
    Model tier: cheap (haiku)
    Output: lead score, intent/fit flags, checkout strategy
    """
    agent = lead_qualifier()
    task = score_lead_task(agent=agent, lead_context=lead_context)

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


def run(lead_context: str) -> str:
    crew = build_crew(lead_context)
    result = crew.kickoff()
    return str(result)
