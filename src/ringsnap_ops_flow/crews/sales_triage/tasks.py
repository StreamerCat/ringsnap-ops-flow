"""Sales triage crew tasks."""
from crewai import Task
from .agents import lead_qualifier


def score_lead_task(agent: "Agent", lead_context: str) -> Task:
    return Task(
        description=(
            f"Score this qualified lead and determine checkout strategy.\n\n"
            f"Lead context:\n{lead_context}\n\n"
            "Output JSON with:\n"
            "- lead_score (0-100)\n"
            "- is_high_intent (bool)\n"
            "- is_high_fit (bool)\n"
            "- recommended_plan (string)\n"
            "- checkout_strategy: 'send_now' | 'call_back_first' | 'low_priority_nurture'\n"
            "- callback_recommended (bool, only if score >= 75 and checkout not completed)\n"
            "- reasoning (1-2 sentences max)\n"
        ),
        expected_output="JSON object with lead_score, is_high_intent, is_high_fit, recommended_plan, checkout_strategy, callback_recommended, reasoning",
        agent=agent,
    )
