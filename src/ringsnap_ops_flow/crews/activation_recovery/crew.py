"""Activation recovery crew — handles payment and provisioning failures."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import recovery_engineer
from .tasks import recovery_plan_task


def build_crew(failure_context: str) -> Crew:
    agent = recovery_engineer()
    task = recovery_plan_task(agent=agent, failure_context=failure_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(failure_context: str) -> str:
    return str(build_crew(failure_context).kickoff())
