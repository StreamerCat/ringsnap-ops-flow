"""Executive digest tasks."""
from crewai import Task
from ...tools.digest_tool import DigestFormatterTool


def write_digest_task(agent, metrics: dict, date: str = "") -> Task:
    formatter = DigestFormatterTool()
    formatted = formatter._run(metrics=metrics, date=date)

    return Task(
        description=(
            f"Review this pre-formatted digest and add a 'Today's Priority Actions' section "
            f"with 1-3 specific, actionable items for the founder.\n\n"
            f"Pre-formatted digest:\n{formatted}\n\n"
            "Append a ## Today's Priority Actions section with a numbered list. "
            "Keep total digest under 400 words. Return the complete digest markdown."
        ),
        expected_output="Complete founder digest in markdown format with Today's Priority Actions section",
        agent=agent,
    )
