"""Onboarding activation tasks."""
from crewai import Task


def diagnose_stall_task(agent, stall_context: str) -> Task:
    return Task(
        description=(
            f"Diagnose this onboarding stall and recommend re-engagement action.\n\n"
            f"Context:\n{stall_context}\n\n"
            "Output JSON with:\n"
            "- last_completed_step (string)\n"
            "- stall_reason_hypothesis (1 sentence)\n"
            "- recovery_action: 'reopen_task' | 'send_reminder' | 'recommend_callback' | 'escalate_to_support'\n"
            "- safe_to_auto_execute (bool)\n"
            "- urgency: 'low' | 'medium' | 'high'\n"
            "- summary (1 sentence)\n"
        ),
        expected_output="JSON with last_completed_step, stall_reason_hypothesis, recovery_action, safe_to_auto_execute, urgency, summary",
        agent=agent,
    )
