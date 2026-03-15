"""Tests for execution autonomy policy."""

from ringsnap_ops_flow.execution.policy import AutonomyPolicy


def test_policy_allows_low_risk_auto_patch():
    policy = AutonomyPolicy.from_default_file()
    decision = policy.classify("seo_meta_schema", ["docs/runbooks/incident.md"])
    assert decision.mode == "auto_patch"


def test_policy_pr_only_for_activation_class():
    policy = AutonomyPolicy.from_default_file()
    decision = policy.classify("activation_failure_recovery", ["src/ringsnap_ops_flow/crews/activation_recovery/tasks.py"])
    assert decision.mode == "pr_only"


def test_policy_blocks_sensitive_paths_even_if_low_risk_class():
    policy = AutonomyPolicy.from_default_file()
    decision = policy.classify("seo_meta_schema", ["src/ringsnap_ops_flow/deterministic/payment_handler.py"])
    assert decision.mode == "blocked"
