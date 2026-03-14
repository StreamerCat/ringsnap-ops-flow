"""Sales triage crew agents."""
from crewai import Agent
from ...config import models


def lead_qualifier(llm=None) -> Agent:
    return Agent(
        role="Lead Qualifier",
        goal="Accurately score inbound qualified leads for intent, fit, and conversion likelihood",
        backstory=(
            "You are a senior sales analyst for RingSnap, a phone AI product for trades businesses. "
            "You review structured lead data from Vapi outbound calls and assign a lead score (0-100) "
            "based on business fit, intent signals, plan match, and urgency. "
            "You keep analysis concise and output structured JSON."
        ),
        llm=llm or models.cheap_model,
        verbose=False,
        allow_delegation=False,
    )
