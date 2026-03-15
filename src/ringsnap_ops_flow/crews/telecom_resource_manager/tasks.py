"""Telecom resource manager tasks."""

from crewai import Task

from ..repo_awareness import repo_inspection_block


def check_telecom_dependencies_task(agent, telecom_context: str) -> Task:
    return Task(
        description=(
            f"Analyze telecom resource status and diagnose this provisioning failure.\n\n"
            f"Context:\n{telecom_context}\n\n"
            f"{repo_inspection_block('telecom provisioning workflow, Twilio/Vapi integrations, and pool management logic')}\n"
            "Output JSON with:\n"
            "- phone_pool_status: 'healthy' | 'low' | 'empty'\n"
            "- phone_pool_count (int, available numbers)\n"
            "- failed_dependency: 'phone_pool' | 'vapi_api' | 'twilio_api' | 'supabase' | 'unknown'\n"
            "- safe_retry_possible (bool)\n"
            "- recommended_action: 'retry_assign' | 'seed_pool' | 'check_vapi_status' | 'manual_review'\n"
            "- estimated_recovery_time_minutes (int)\n"
            "- summary (1-2 sentences)\n"
        ),
        expected_output="JSON with dependency diagnosis and repo-verified evidence",
        agent=agent,
    )
