"""Prompt voice QA crew."""
from __future__ import annotations
from crewai import Crew, Process
from .agents import prompt_qa_analyst
from .tasks import qa_prompt_template_task


def build_crew(prompt_context: str) -> Crew:
    agent = prompt_qa_analyst()
    task = qa_prompt_template_task(agent=agent, prompt_context=prompt_context)
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def run(prompt_context: str) -> str:
    return str(build_crew(prompt_context).kickoff())
