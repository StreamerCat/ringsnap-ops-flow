"""Usage product insights tasks."""
from crewai import Task


def analyze_usage_task(agent, usage_context: str) -> Task:
    return Task(
        description=(
            f"Analyze this batched usage data and produce product insights.\n\n"
            f"Data:\n{usage_context}\n\n"
            "Output JSON with:\n"
            "- top_insights (list of up to 5 strings)\n"
            "- churn_risk_signals (list of strings)\n"
            "- feature_adoption_highlights (list of strings)\n"
            "- recommended_product_actions (list of up to 3 strings)\n"
            "- summary (2 sentences max)\n"
        ),
        expected_output="JSON with top_insights, churn_risk_signals, feature_adoption_highlights, recommended_product_actions, summary",
        agent=agent,
    )
