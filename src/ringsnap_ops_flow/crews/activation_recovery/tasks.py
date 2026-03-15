"""Activation recovery tasks."""

from crewai import Task

from ..repo_awareness import repo_inspection_block


def recovery_plan_task(agent, failure_context: str) -> Task:
    return Task(
        description=(
            f"Analyze this activation failure and produce a recovery plan.\n\n"
            f"Context:\n{failure_context}\n\n"
            f"{repo_inspection_block('activation, provisioning, and payment failure paths')}\n"
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
        expected_output="JSON recovery plan with runtime + repo evidence and safe retry guidance",
        agent=agent,
    )
