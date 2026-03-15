"""Support triage tasks."""

from crewai import Task

from ..repo_awareness import repo_inspection_block


def triage_tickets_task(agent, tickets_context: str) -> Task:
    return Task(
        description=(
            f"Triage these support tickets.\n\n"
            f"Tickets:\n{tickets_context}\n\n"
            "When tickets indicate technical/system issues, inspect relevant RingSnap repo files before deciding escalation. "
            "For purely account/billing content, repo inspection is optional.\n"
            f"{repo_inspection_block('technical incidents from support tickets')}\n"
            "For each ticket output:\n"
            "- ticket_id\n"
            "- category: 'billing' | 'technical' | 'onboarding' | 'feature_request' | 'other'\n"
            "- priority: 'low' | 'medium' | 'high' | 'urgent'\n"
            "- escalate (bool)\n"
            "- one_line_summary (string)\n"
            "\nReturn as JSON array."
        ),
        expected_output="JSON array of triaged tickets with priority plus repo evidence fields",
        agent=agent,
    )
