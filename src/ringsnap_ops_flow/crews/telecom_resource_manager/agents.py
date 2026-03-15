"""Telecom resource manager crew agents."""

from ...config import models
from ..repo_awareness import build_agent


def telecom_analyst(llm=None):
    return build_agent(
        role="Telecom Resource Analyst",
        goal="Check telecom resource availability and diagnose provisioning dependency failures",
        backstory=(
            "You manage telecom resources for RingSnap: phone number pool health, "
            "Vapi assistant provisioning status, and number lifecycle states. "
            "When provisioning fails, you identify the exact dependency that failed "
            "and recommend safe recovery steps. You never recommend releasing active numbers "
            "or modifying live assistant configurations without human approval."
        ),
        llm=llm or models.cheap_model,
        enable_repo_read=True,
    )
