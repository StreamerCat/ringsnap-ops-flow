"""Sales triage crew agents."""

from ...config import models
from ..repo_awareness import build_agent


def lead_qualifier(llm=None):
    return build_agent(
        role="Lead Qualifier",
        goal="Accurately score inbound qualified leads for intent, fit, and conversion likelihood",
        backstory=(
            "You are a senior sales analyst for RingSnap, a phone AI product for trades businesses. "
            "You review structured lead data from Vapi outbound calls and assign a lead score (0-100) "
            "based on business fit, intent signals, plan match, and urgency. "
            "You keep analysis concise and output structured JSON."
        ),
        llm=llm or models.cheap_model,
        enable_repo_read=False,
    )
