"""
Configuration loader for RingSnap Ops Flow.
Merges ops_config.yaml thresholds with environment variable secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - local fallback for constrained test environments
    class _EnvField:
        def __init__(self, default: Any = None, alias: str | None = None):
            self.default = default
            self.alias = alias

    def Field(default=None, alias=None, **_kwargs):
        return _EnvField(default=default, alias=alias)

    def SettingsConfigDict(**kwargs):
        return kwargs

    class BaseSettings:
        def __init__(self, **kwargs):
            for name, value in self.__class__.__dict__.items():
                if isinstance(value, _EnvField):
                    env_key = value.alias or name.upper()
                    resolved = kwargs.get(name, os.getenv(env_key, value.default))
                    setattr(self, name, resolved)


def _load_yaml() -> dict[str, Any]:
    config_path = Path(__file__).parent.parent.parent / "config" / "ops_config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml = _load_yaml()


class ExecutionConfig:
    max_executions_per_day: int = _yaml.get("execution", {}).get("max_executions_per_day", 500)
    max_retries_per_workflow: int = _yaml.get("execution", {}).get("max_retries_per_workflow", 3)
    max_rescue_attempts: int = _yaml.get("execution", {}).get("max_rescue_attempts", 2)
    debounce_seconds: int = _yaml.get("execution", {}).get("debounce_seconds", 60)
    safe_mode_execution_factor: float = _yaml.get("execution", {}).get("safe_mode_execution_factor", 0.25)


class ThresholdConfig:
    onboarding_stall_threshold_hours: int = _yaml.get("thresholds", {}).get("onboarding_stall_threshold_hours", 24)
    funnel_failure_threshold_pct: float = _yaml.get("thresholds", {}).get("funnel_failure_threshold_pct", 0.30)
    checkout_completion_threshold: float = _yaml.get("thresholds", {}).get("checkout_completion_threshold", 0.50)
    activation_failure_threshold: float = _yaml.get("thresholds", {}).get("activation_failure_threshold", 0.20)
    expensive_provisioning_failure_threshold: float = _yaml.get("thresholds", {}).get(
        "expensive_provisioning_failure_threshold", 0.15
    )
    duplicate_signup_cooldown_minutes: int = _yaml.get("thresholds", {}).get("duplicate_signup_cooldown_minutes", 60)
    pending_signup_expiry_hours: int = _yaml.get("thresholds", {}).get("pending_signup_expiry_hours", 48)
    human_callback_score_threshold: int = _yaml.get("thresholds", {}).get("human_callback_score_threshold", 75)
    outbound_safe_mode_threshold: float = _yaml.get("thresholds", {}).get("outbound_safe_mode_threshold", 0.40)


class ModelConfig:
    cheap_model: str = _yaml.get("models", {}).get("cheap_model", "claude-haiku-4-5-20251001")
    default_model: str = _yaml.get("models", {}).get("default_model", "claude-sonnet-4-6")
    reasoning_model: str = _yaml.get("models", {}).get("reasoning_model", "claude-opus-4-6")


class CostConfig:
    daily_llm_budget_usd: float = _yaml.get("cost", {}).get("daily_llm_budget_usd", 10.0)
    alert_at_pct: float = _yaml.get("cost", {}).get("alert_at_pct", 0.80)
    token_cost_estimates: dict = _yaml.get("cost", {}).get("token_cost_estimates", {})


class CrewsConfig:
    max_daily_executions: dict[str, int] = _yaml.get("crews", {}).get("max_daily_executions", {})
    cooldown_minutes: dict[str, int] = _yaml.get("crews", {}).get("cooldown_minutes", {})

    def get_max_daily(self, module_name: str) -> int:
        return self.max_daily_executions.get(module_name, ExecutionConfig.max_executions_per_day)

    def get_cooldown_minutes(self, module_name: str) -> int:
        return self.cooldown_minutes.get(module_name, self.cooldown_minutes.get("default", 60))


class SafeModeConfig:
    critical_only_modules: list[str] = _yaml.get("safe_mode", {}).get(
        "critical_only_modules",
        ["activation_recovery", "abuse_guard", "executive_digest", "signup_conversion_guard", "cost_cogs_monitor"],
    )


class OpsSettings(BaseSettings):
    """Environment variable settings. All secrets come from .env, never from yaml."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_OPS_WEBHOOK_SECRET")
    vapi_api_key: str = Field(default="", alias="VAPI_API_KEY")
    vapi_webhook_secret: str = Field(default="", alias="VAPI_WEBHOOK_SECRET")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(default="", alias="TWILIO_FROM_NUMBER")
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    resend_from_email: str = Field(default="ops@ringsnap.com", alias="RESEND_FROM_EMAIL")
    ops_webhook_secret: str = Field(default="", alias="OPS_WEBHOOK_SECRET")
    posthog_api_key: str = Field(default="", alias="POSTHOG_API_KEY")
    posthog_host: str = Field(default="https://us.i.posthog.com", alias="POSTHOG_HOST")
    ops_flow_enabled: bool = Field(default=True, alias="OPS_FLOW_ENABLED")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    port: int = Field(default=8080, alias="PORT")
    ops_execution_enabled: bool = Field(default=False, alias="OPS_EXECUTION_ENABLED")
    ops_execution_dry_run: bool = Field(default=True, alias="OPS_EXECUTION_DRY_RUN")
    ringsnap_repo: str = Field(default="", alias="RINGSNAP_REPO")
    ringsnap_branch: str = Field(default="main", alias="RINGSNAP_BRANCH")
    ringsnap_marketing_url: str = Field(default="https://getringsnap.com", alias="RINGSNAP_MARKETING_URL")
    ringsnap_app_url: str = Field(default="https://app.ringsnap.com", alias="RINGSNAP_APP_URL")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_owner: str = Field(default="", alias="GITHUB_OWNER")
    github_repo: str = Field(default="", alias="GITHUB_REPO")

    @property
    def is_stub_mode(self) -> bool:
        return not self.anthropic_api_key or not self.supabase_url

    @property
    def ringsnap_repo_owner(self) -> str:
        if self.github_owner:
            return self.github_owner
        if "/" in self.ringsnap_repo:
            return self.ringsnap_repo.split("/", 1)[0]
        return ""

    @property
    def ringsnap_repo_name(self) -> str:
        if self.github_repo:
            return self.github_repo
        if "/" in self.ringsnap_repo:
            return self.ringsnap_repo.split("/", 1)[1]
        return self.ringsnap_repo


settings = OpsSettings()
execution = ExecutionConfig()
thresholds = ThresholdConfig()
models = ModelConfig()
cost = CostConfig()
crews = CrewsConfig()
safe_mode_cfg = SafeModeConfig()
