"""Autonomy policy for safe repo patch execution lanes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PolicyDecision:
    mode: str
    reason: str


DEFAULT_POLICY = {
    "auto_patch_classes": [
        "marketing_lighthouse",
        "seo_meta_schema",
        "accessibility_ui",
        "docs_runbooks_tests_config",
    ],
    "pr_only_classes": [
        "activation_failure_recovery",
        "signup_failure_recovery",
        "support_technical_hotfix",
    ],
    "blocked_classes": ["billing", "provisioning", "auth", "stripe", "vapi", "onboarding", "webhook"],
    "blocked_path_prefixes": [
        "src/ringsnap_ops_flow/deterministic/payment_handler.py",
        "src/ringsnap_ops_flow/deterministic/provisioning_handler.py",
        "src/ringsnap_ops_flow/deterministic/signup_handler.py",
        "src/ringsnap_ops_flow/adapters/stripe_adapter.py",
        "src/ringsnap_ops_flow/adapters/vapi_adapter.py",
        "src/ringsnap_ops_flow/main.py",
    ],
    "allowed_low_risk_prefixes": ["docs/", "tests/", "config/", "marketing/", "website/", "web/"],
}


class AutonomyPolicy:
    def __init__(self, raw: dict):
        self.raw = raw
        self.auto_patch_classes = set(raw.get("auto_patch_classes", []))
        self.pr_only_classes = set(raw.get("pr_only_classes", []))
        self.blocked_classes = set(raw.get("blocked_classes", []))
        self.blocked_path_prefixes = tuple(raw.get("blocked_path_prefixes", []))
        self.allowed_low_risk_prefixes = tuple(raw.get("allowed_low_risk_prefixes", []))

    @classmethod
    def from_default_file(cls) -> "AutonomyPolicy":
        policy_file = Path(__file__).resolve().parents[3] / "config" / "autonomy_policy.yaml"
        raw = {}
        if policy_file.exists():
            with open(policy_file) as handle:
                raw = yaml.safe_load(handle) or {}
        if not raw:
            raw = DEFAULT_POLICY
        return cls(raw)

    def classify(self, change_class: str, changed_paths: list[str]) -> PolicyDecision:
        if change_class in self.blocked_classes:
            return PolicyDecision(mode="blocked", reason=f"change_class '{change_class}' is blocked")

        if any(self._is_blocked_path(path) for path in changed_paths):
            return PolicyDecision(mode="blocked", reason="one or more changed paths are blocked from automation")

        if change_class in self.pr_only_classes:
            return PolicyDecision(mode="pr_only", reason=f"change_class '{change_class}' requires human approval")

        if change_class in self.auto_patch_classes:
            if self._paths_within_low_risk_allowlist(changed_paths):
                return PolicyDecision(mode="auto_patch", reason="class/path combination is allowlisted")
            return PolicyDecision(mode="pr_only", reason="paths outside low-risk prefixes require human approval")

        return PolicyDecision(mode="pr_only", reason="unclassified change class defaults to PR-only")

    def _is_blocked_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.blocked_path_prefixes)

    def _paths_within_low_risk_allowlist(self, paths: list[str]) -> bool:
        if not paths:
            return False
        return all(any(path.startswith(prefix) for prefix in self.allowed_low_risk_prefixes) for path in paths)
