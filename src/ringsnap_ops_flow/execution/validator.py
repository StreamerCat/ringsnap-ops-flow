"""Targeted validation runner for scoped patch workflows."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    command: str
    success: bool
    output: str


VALIDATION_COMMANDS = {
    "marketing_lighthouse": ["npm run lint", "npm run test -- --runInBand"],
    "seo_meta_schema": ["npm run lint"],
    "accessibility_ui": ["npm run lint", "npm run test -- --runInBand"],
    "docs_runbooks_tests_config": ["pytest -q tests/test_config.py"],
    "activation_failure_recovery": ["pytest -q tests/test_provisioning_handler.py tests/test_payment_handler.py"],
}


class TargetedValidator:
    def commands_for(self, change_class: str) -> list[str]:
        return VALIDATION_COMMANDS.get(change_class, [])

    def run(self, change_class: str, *, execute: bool = False, workdir: str = ".") -> list[ValidationResult]:
        commands = self.commands_for(change_class)
        results: list[ValidationResult] = []
        for cmd in commands:
            if not execute:
                results.append(ValidationResult(command=cmd, success=True, output="[dry-run] not executed"))
                continue

            proc = subprocess.run(cmd, shell=True, cwd=workdir, capture_output=True, text=True)
            output = (proc.stdout + "\n" + proc.stderr).strip()
            results.append(ValidationResult(command=cmd, success=(proc.returncode == 0), output=output))
        return results
