"""Outbound ROI guard crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import roi_analyst
from .tasks import evaluate_campaign_health_task


def build_crew(metrics_context: str) -> Crew:
    agent = roi_analyst()
    task = evaluate_campaign_health_task(agent=agent, metrics_context=metrics_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(metrics_context: str) -> str:
    return str(build_crew(metrics_context).kickoff())
