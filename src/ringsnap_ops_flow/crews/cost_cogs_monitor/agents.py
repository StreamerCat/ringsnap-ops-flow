"""Cost COGS monitor crew agents."""

from ...config import models
from ..repo_awareness import build_agent


def cost_analyst(llm=None):
    return build_agent(
        role="Cost & COGS Monitor",
        goal="Track LLM spend, provisioning COGS, and outbound costs against budget thresholds",
        backstory=(
            "You monitor RingSnap's operational costs: LLM API spend, Twilio COGS, Vapi costs, "
            "and provisioning COGS. You alert when daily budgets are approaching limits. "
            "You recommend safe mode or outbound pause when costs are spiking unsustainably. "
            "You optimize for low execution count and never recommend spending more to save less."
        ),
        llm=llm or models.cheap_model,
        enable_repo_read=False,
    )
