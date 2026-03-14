"""Telecom resource manager tasks."""
from crewai import Task


def check_telecom_dependencies_task(agent, telecom_context: str) -> Task:
    return Task(
        description=(
            f"Analyze telecom resource status and diagnose this provisioning failure.\n\n"
            f"Context:\n{telecom_context}\n\n"
            "Output JSON with:\n"
            "- phone_pool_status: 'healthy' | 'low' | 'empty'\n"
            "- phone_pool_count (int, available numbers)\n"
            "- failed_dependency: 'phone_pool' | 'vapi_api' | 'twilio_api' | 'supabase' | 'unknown'\n"
            "- safe_retry_possible (bool)\n"
            "- recommended_action: 'retry_assign' | 'seed_pool' | 'check_vapi_status' | 'manual_review'\n"
            "- estimated_recovery_time_minutes (int)\n"
            "- summary (1-2 sentences)\n"
        ),
        expected_output="JSON with phone_pool_status, failed_dependency, safe_retry_possible, recommended_action, summary",
        agent=agent,
    )
