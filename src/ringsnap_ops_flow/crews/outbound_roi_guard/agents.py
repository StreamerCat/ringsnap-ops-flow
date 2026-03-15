"""Outbound ROI guard agents."""

from ...config import models
from ..repo_awareness import build_agent


def roi_analyst(llm=None):
    return build_agent(
        role="Outbound ROI Analyst",
        goal="Evaluate outbound campaign health metrics and recommend safe mode or volume adjustments",
        backstory=(
            "You analyze RingSnap outbound sales campaign metrics: checkout completion rates, "
            "activation rates, and cost per acquisition. You recommend outbound safe mode when "
            "downstream conversion systems degrade. You prefer reducing volume over pausing entirely."
        ),
        llm=llm or models.cheap_model,
        enable_repo_read=True,
    )
