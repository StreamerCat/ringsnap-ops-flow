"""Usage product insights crew agents."""

from ...config import models
from ..repo_awareness import build_agent


def product_analyst(llm=None):
    return build_agent(
        role="Product Usage Analyst",
        goal="Identify actionable product insights from batched usage data and funnel metrics",
        backstory=(
            "You analyze RingSnap product usage data in scheduled batch jobs. "
            "You surface patterns in call outcomes, feature adoption, and churn signals. "
            "You write concise, actionable insights (max 5 bullet points). "
            "You are not triggered by individual events — only batched summaries."
        ),
        llm=llm or models.cheap_model,
        enable_repo_read=False,
    )
