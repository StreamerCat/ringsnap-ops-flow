"""Structural tests for repo-aware agent/tool/task configuration."""

from ringsnap_ops_flow.crews.abuse_guard.agents import abuse_analyst
from ringsnap_ops_flow.crews.activation_recovery.agents import recovery_engineer
from ringsnap_ops_flow.crews.cost_cogs_monitor.agents import cost_analyst
from ringsnap_ops_flow.crews.onboarding_activation.agents import onboarding_coach
from ringsnap_ops_flow.crews.outbound_roi_guard.agents import roi_analyst
from ringsnap_ops_flow.crews.prompt_voice_qa.agents import prompt_qa_analyst
from ringsnap_ops_flow.crews.sales_triage.agents import lead_qualifier
from ringsnap_ops_flow.crews.signup_conversion_guard.agents import recovery_analyst
from ringsnap_ops_flow.crews.support_triage.agents import support_triager
from ringsnap_ops_flow.crews.telecom_resource_manager.agents import telecom_analyst
from ringsnap_ops_flow.crews.usage_product_insights.agents import product_analyst

from ringsnap_ops_flow.crews.activation_recovery.tasks import recovery_plan_task
from ringsnap_ops_flow.crews.prompt_voice_qa.tasks import qa_prompt_template_task
from ringsnap_ops_flow.crews.sales_triage.tasks import score_lead_task


def _tool_names(agent):
    return {tool.name for tool in getattr(agent, "tools", [])}


def test_repo_tool_attached_to_repo_diagnostic_agents():
    for agent_factory in [
        abuse_analyst,
        recovery_engineer,
        onboarding_coach,
        roi_analyst,
        prompt_qa_analyst,
        recovery_analyst,
        support_triager,
        telecom_analyst,
    ]:
        assert "inspect_ringsnap_repo" in _tool_names(agent_factory(llm="noop"))


def test_repo_tool_not_attached_to_runtime_only_agents():
    for agent_factory in [cost_analyst, lead_qualifier, product_analyst]:
        assert "inspect_ringsnap_repo" not in _tool_names(agent_factory(llm="noop"))


def test_repo_aware_tasks_require_repo_inspection_fields():
    description = recovery_plan_task(agent=recovery_engineer(llm="noop"), failure_context="ctx").description
    assert "Repo-aware requirement" in description
    assert "repo_files_checked" in description
    assert "repo_evidence" in description

    qa_description = qa_prompt_template_task(agent=prompt_qa_analyst(llm="noop"), prompt_context="ctx").description
    assert "Repo-aware requirement" in qa_description


def test_runtime_only_task_declares_runtime_scope():
    description = score_lead_task(agent=lead_qualifier(llm="noop"), lead_context="ctx").description
    assert "runtime-only" in description
