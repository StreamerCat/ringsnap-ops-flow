"""Prompt voice QA crew agents."""
from crewai import Agent
from ...config import models


def prompt_qa_analyst(llm=None) -> Agent:
    return Agent(
        role="Voice Prompt QA Analyst",
        goal="Verify prompt template variable integrity and validate fallback/objection handling paths",
        backstory=(
            "You audit Vapi AI voice prompt templates for RingSnap. "
            "You check that all template variables resolve, fallback scripts exist, "
            "objection handling paths are defined, and silence handling is configured. "
            "You output a structured QA report with pass/fail for each check."
        ),
        llm=llm or models.cheap_model,
        verbose=False,
        allow_delegation=False,
    )
