"""Prompt voice QA crew agents."""

from ...config import models
from ..repo_awareness import build_agent


def prompt_qa_analyst(llm=None):
    return build_agent(
        role="Voice Prompt QA Analyst",
        goal="Verify prompt template variable integrity and validate fallback/objection handling paths",
        backstory=(
            "You audit Vapi AI voice prompt templates for RingSnap. "
            "You check that all template variables resolve, fallback scripts exist, "
            "objection handling paths are defined, and silence handling is configured. "
            "You output a structured QA report with pass/fail for each check."
        ),
        llm=llm or models.cheap_model,
        enable_repo_read=True,
    )
