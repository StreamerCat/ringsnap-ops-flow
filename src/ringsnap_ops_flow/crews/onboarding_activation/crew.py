"""Onboarding activation crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import onboarding_coach
from .tasks import diagnose_stall_task


def build_crew(stall_context: str) -> Crew:
    agent = onboarding_coach()
    task = diagnose_stall_task(agent=agent, stall_context=stall_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(stall_context: str) -> str:
    return str(build_crew(stall_context).kickoff())
