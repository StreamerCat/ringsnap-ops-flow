"""Signup conversion guard tasks."""
from crewai import Task


def diagnose_signup_failure_task(agent, failure_context: str) -> Task:
    return Task(
        description=(
            f"Analyze this signup failure and recommend recovery action.\n\n"
            f"Failure context:\n{failure_context}\n\n"
            "Output JSON with:\n"
            "- failure_phase (string: which step failed)\n"
            "- root_cause (1 sentence)\n"
            "- recovery_action: 'resend_link' | 'retry_stage1' | 'mark_manual_review' | 'expire_and_create_new'\n"
            "- safe_to_auto_execute (bool)\n"
            "- alert_required (bool)\n"
            "- reasoning (1-2 sentences)\n"
        ),
        expected_output="JSON with failure_phase, root_cause, recovery_action, safe_to_auto_execute, alert_required, reasoning",
        agent=agent,
    )
