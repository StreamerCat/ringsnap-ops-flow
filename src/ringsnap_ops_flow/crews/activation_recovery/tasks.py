"""Activation recovery tasks."""
from crewai import Task


def recovery_plan_task(agent, failure_context: str) -> Task:
    return Task(
        description=(
            f"Analyze this activation failure and produce a recovery plan.\n\n"
            f"Context:\n{failure_context}\n\n"
            "Output JSON with:\n"
            "- failure_type: 'payment' | 'provisioning' | 'activation'\n"
            "- failure_point (exact step that failed)\n"
            "- safe_retry_steps (list of steps that can be retried)\n"
            "- destructive_steps_to_skip (list of steps that must NOT be retried)\n"
            "- alert_severity: 'warning' | 'critical'\n"
            "- mark_for_manual_review (bool)\n"
            "- pause_stage2_recommended (bool)\n"
            "- summary (2 sentences max)\n"
        ),
        expected_output="JSON recovery plan with failure_type, failure_point, safe_retry_steps, alert_severity, mark_for_manual_review, pause_stage2_recommended, summary",
        agent=agent,
    )
