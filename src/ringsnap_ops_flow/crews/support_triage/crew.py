"""Support triage crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import support_triager
from .tasks import triage_tickets_task


def build_crew(tickets_context: str) -> Crew:
    agent = support_triager()
    task = triage_tickets_task(agent=agent, tickets_context=tickets_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(tickets_context: str) -> str:
    return str(build_crew(tickets_context).kickoff())
