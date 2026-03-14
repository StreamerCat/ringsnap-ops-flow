"""Cost COGS monitor crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import cost_analyst
from .tasks import analyze_costs_task


def build_crew(cost_context: str) -> Crew:
    agent = cost_analyst()
    task = analyze_costs_task(agent=agent, cost_context=cost_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(cost_context: str) -> str:
    return str(build_crew(cost_context).kickoff())
