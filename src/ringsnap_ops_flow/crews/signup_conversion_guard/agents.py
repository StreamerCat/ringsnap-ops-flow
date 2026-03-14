"""Signup conversion guard agents."""
from crewai import Agent
from ...config import models


def recovery_analyst(llm=None) -> Agent:
    return Agent(
        role="Signup Recovery Analyst",
        goal="Diagnose signup failures and recommend the safest non-destructive recovery action",
        backstory=(
            "You are a reliability engineer for RingSnap. You analyze signup and account creation failures, "
            "determine the exact failure point, and recommend one of these actions: "
            "resend_link | retry_stage1 | mark_manual_review | expire_and_create_new. "
            "You never recommend destructive actions or changes to production infrastructure."
        ),
        llm=llm or models.cheap_model,
        verbose=False,
        allow_delegation=False,
    )
