"""Outbound ROI guard tasks."""
from crewai import Task


def evaluate_campaign_health_task(agent, metrics_context: str) -> Task:
    return Task(
        description=(
            f"Evaluate outbound campaign health and recommend action.\n\n"
            f"Metrics:\n{metrics_context}\n\n"
            "Output JSON with:\n"
            "- health_status: 'healthy' | 'degraded' | 'critical'\n"
            "- safe_mode_recommended (bool)\n"
            "- volume_reduction_pct (0-100, suggested outbound volume reduction)\n"
            "- key_issues (list of strings)\n"
            "- recommended_actions (list of strings, safe non-destructive only)\n"
            "- summary (2 sentences max)\n"
        ),
        expected_output="JSON with health_status, safe_mode_recommended, volume_reduction_pct, key_issues, recommended_actions, summary",
        agent=agent,
    )
