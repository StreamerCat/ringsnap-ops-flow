"""Cost COGS monitor tasks."""
from crewai import Task


def analyze_costs_task(agent, cost_context: str) -> Task:
    return Task(
        description=(
            f"Analyze current operational costs and recommend actions.\n\n"
            f"Cost data:\n{cost_context}\n\n"
            "Output JSON with:\n"
            "- budget_status: 'ok' | 'warning' | 'critical'\n"
            "- daily_llm_cost_usd (float)\n"
            "- budget_pct_used (float, 0.0-1.0)\n"
            "- cogs_per_activated_trial_usd (float, estimate)\n"
            "- safe_mode_recommended (bool)\n"
            "- cost_reduction_actions (list of strings)\n"
            "- summary (2 sentences max)\n"
        ),
        expected_output="JSON with budget_status, daily_llm_cost_usd, budget_pct_used, safe_mode_recommended, cost_reduction_actions, summary",
        agent=agent,
    )
