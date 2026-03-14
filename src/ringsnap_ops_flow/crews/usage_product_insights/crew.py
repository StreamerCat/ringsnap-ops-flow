"""Usage product insights crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import product_analyst
from .tasks import analyze_usage_task


def build_crew(usage_context: str) -> Crew:
    agent = product_analyst()
    task = analyze_usage_task(agent=agent, usage_context=usage_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(usage_context: str) -> str:
    return str(build_crew(usage_context).kickoff())
