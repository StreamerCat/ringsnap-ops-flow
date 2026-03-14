"""Support triage tasks."""
from crewai import Task


def triage_tickets_task(agent, tickets_context: str) -> Task:
    return Task(
        description=(
            f"Triage these support tickets.\n\n"
            f"Tickets:\n{tickets_context}\n\n"
            "For each ticket output:\n"
            "- ticket_id\n"
            "- category: 'billing' | 'technical' | 'onboarding' | 'feature_request' | 'other'\n"
            "- priority: 'low' | 'medium' | 'high' | 'urgent'\n"
            "- escalate (bool)\n"
            "- one_line_summary (string)\n"
            "\nReturn as JSON array."
        ),
        expected_output="JSON array of triaged tickets with ticket_id, category, priority, escalate, one_line_summary",
        agent=agent,
    )
