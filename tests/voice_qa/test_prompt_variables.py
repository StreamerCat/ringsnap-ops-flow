"""
Voice QA: Prompt template variable integrity tests.
PROTECTED: Prompt templates must always resolve all variables.
These tests prevent undefined variables from reaching live calls.
"""

import re
import pytest


# Regex to find unresolved template variables like {variable_name} or {{variable}}
UNRESOLVED_VAR_PATTERN = re.compile(r"\{\{?\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\}?\}")


def _check_template_for_unresolved(template: str) -> list[str]:
    """Returns list of any unresolved template variable patterns found."""
    return UNRESOLVED_VAR_PATTERN.findall(template)


SAMPLE_VAPI_SYSTEM_PROMPT = """
You are {company_name}'s AI receptionist.
Your goal is to qualify callers and schedule appointments.
Current time zone: {timezone}.
Business owner: {owner_name}.
Trade specialty: {trade}.
"""

SAMPLE_PROMPT_WITH_MISSING_VARS = """
You are {company_name}'s AI receptionist.
Your goal is to qualify callers for {undefined_variable_1}.
Contact: {missing_contact_info}.
"""

GOOD_RESOLVED_PROMPT = """
You are Smith Plumbing's AI receptionist.
Your goal is to qualify callers and schedule appointments.
Current time zone: America/Denver.
Business owner: John Smith.
Trade specialty: plumbing.
"""


def test_resolved_prompt_has_no_unresolved_vars():
    """A fully resolved prompt should have no unresolved variables."""
    unresolved = _check_template_for_unresolved(GOOD_RESOLVED_PROMPT)
    assert len(unresolved) == 0, f"Found unresolved vars: {unresolved}"


def test_template_with_vars_is_flagged():
    """A prompt with template variables is flagged for review (not safe for production)."""
    unresolved = _check_template_for_unresolved(SAMPLE_VAPI_SYSTEM_PROMPT)
    assert len(unresolved) > 0, "Expected to find template variables"


def test_prompt_with_missing_vars_is_flagged():
    """PROTECTED: Prompts with missing/undefined variables must be caught before deployment."""
    unresolved = _check_template_for_unresolved(SAMPLE_PROMPT_WITH_MISSING_VARS)
    assert len(unresolved) > 0


def test_required_template_variables_all_present():
    """
    Required variables for RingSnap phone sales prompts.
    All must be resolvable from account data before deployment.
    """
    required_vars = [
        "company_name",
        "timezone",
        "owner_name",
        "trade",
    ]
    # Check that the sample template contains all required vars as placeholders
    for var in required_vars:
        assert "{" + var + "}" in SAMPLE_VAPI_SYSTEM_PROMPT, f"Required var '{var}' missing from template"


def test_prompt_length_within_limits():
    """Voice prompts should not exceed reasonable length for phone context."""
    max_chars = 5000  # Vapi system prompt practical limit
    assert len(GOOD_RESOLVED_PROMPT) <= max_chars
