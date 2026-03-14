"""Executive digest crew — writes the daily founder digest."""
from __future__ import annotations
from datetime import datetime
from crewai import Crew, Process
from .agents import digest_writer
from .tasks import write_digest_task


def build_crew(metrics: dict, date: str = "") -> Crew:
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    agent = digest_writer()
    task = write_digest_task(agent=agent, metrics=metrics, date=date)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(metrics: dict, date: str = "") -> str:
    return str(build_crew(metrics, date).kickoff())
