"""Onboarding activation tasks."""

from crewai import Task

from ..repo_awareness import repo_inspection_block


def diagnose_stall_task(agent, stall_context: str) -> Task:
    return Task(
        description=(
            f"Diagnose this onboarding stall and recommend re-engagement action.\n\n"
            f"Context:\n{stall_context}\n\n"
            f"{repo_inspection_block('onboarding flow steps, gating logic, and reminder/callback triggers')}\n"
            "Output JSON with:\n"
            "- last_completed_step (string)\n"
            "- stall_reason_hypothesis (1 sentence)\n"
            "- recovery_action: 'reopen_task' | 'send_reminder' | 'recommend_callback' | 'escalate_to_support'\n"
            "- safe_to_auto_execute (bool)\n"
            "- urgency: 'low' | 'medium' | 'high'\n"
            "- summary (1 sentence)\n"
        ),
        expected_output="JSON with onboarding diagnosis plus runtime/repo evidence fields",
        agent=agent,
    )
