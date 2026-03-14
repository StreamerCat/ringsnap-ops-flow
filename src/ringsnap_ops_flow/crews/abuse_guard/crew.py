"""Abuse guard crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import abuse_analyst
from .tasks import analyze_abuse_task


def build_crew(abuse_context: str) -> Crew:
    agent = abuse_analyst()
    task = analyze_abuse_task(agent=agent, abuse_context=abuse_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(abuse_context: str) -> str:
    return str(build_crew(abuse_context).kickoff())
