"""Prompt voice QA tasks."""
from crewai import Task


def qa_prompt_template_task(agent, prompt_context: str) -> Task:
    return Task(
        description=(
            f"Run QA checks on this Vapi voice prompt template.\n\n"
            f"Template:\n{prompt_context}\n\n"
            "Check for:\n"
            "1. Unresolved template variables (e.g. {{undefined_var}})\n"
            "2. Missing fallback script for failed tool calls\n"
            "3. Missing objection handling (price, timing, not interested)\n"
            "4. Missing silence handling\n"
            "5. Missing booking confirmation path\n"
            "6. Overly long monologues (>3 sentences without a question)\n"
            "\nOutput JSON with:\n"
            "- overall_status: 'pass' | 'fail' | 'warnings'\n"
            "- checks (list of {check_name, status: pass|fail|warning, detail})\n"
            "- critical_failures (list of strings)\n"
            "- recommendations (list of strings)\n"
        ),
        expected_output="JSON QA report with overall_status, checks array, critical_failures, recommendations",
        agent=agent,
    )
