"""Telecom resource manager crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import telecom_analyst
from .tasks import check_telecom_dependencies_task


def build_crew(telecom_context: str) -> Crew:
    agent = telecom_analyst()
    task = check_telecom_dependencies_task(agent=agent, telecom_context=telecom_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(telecom_context: str) -> str:
    return str(build_crew(telecom_context).kickoff())
