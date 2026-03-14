"""Tests for config loading."""

import pytest


def test_ops_config_loads():
    """ops_config.yaml must load without errors."""
    from ringsnap_ops_flow.config import (
        execution,
        thresholds,
        models,
        cost,
        crews,
        safe_mode_cfg,
    )
    assert execution.max_executions_per_day > 0
    assert execution.max_retries_per_workflow > 0
    assert thresholds.onboarding_stall_threshold_hours > 0
    assert thresholds.pending_signup_expiry_hours > 0
    assert thresholds.human_callback_score_threshold > 0
    assert models.cheap_model != ""
    assert models.default_model != ""
    assert cost.daily_llm_budget_usd > 0
    assert len(safe_mode_cfg.critical_only_modules) > 0


def test_model_tiers_are_distinct():
    from ringsnap_ops_flow.config import models
    assert models.cheap_model != models.default_model
    assert models.default_model != models.reasoning_model


def test_threshold_values_in_valid_range():
    from ringsnap_ops_flow.config import thresholds
    assert 0.0 < thresholds.checkout_completion_threshold < 1.0
    assert 0.0 < thresholds.activation_failure_threshold < 1.0
    assert 0 < thresholds.human_callback_score_threshold <= 100


def test_crew_max_daily_executions():
    from ringsnap_ops_flow.config import crews
    # executive_digest should have the lowest cap
    digest_cap = crews.get_max_daily("executive_digest")
    sales_cap = crews.get_max_daily("sales_triage")
    assert digest_cap <= sales_cap


def test_settings_stub_mode_without_credentials():
    from ringsnap_ops_flow.config import settings
    # In test environment (no real keys), stub mode should be True
    assert settings.is_stub_mode is True
