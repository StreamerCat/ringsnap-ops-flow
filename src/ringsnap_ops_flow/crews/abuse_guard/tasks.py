"""Abuse guard tasks."""
from crewai import Task


def analyze_abuse_task(agent, abuse_context: str) -> Task:
    return Task(
        description=(
            f"Analyze this abuse/risk signal and recommend protective action.\n\n"
            f"Context:\n{abuse_context}\n\n"
            "Output JSON with:\n"
            "- risk_level: 'low' | 'medium' | 'high' | 'critical'\n"
            "- abuse_type: 'trial_abuse' | 'fake_signup' | 'call_spam' | 'billing_fraud' | 'other'\n"
            "- affected_account_ids (list of strings)\n"
            "- recommended_action: 'block_account' | 'flag_for_review' | 'throttle_calls' | 'alert_founder' | 'no_action'\n"
            "- requires_human_approval (bool, always True for block_account)\n"
            "- confidence: 'low' | 'medium' | 'high'\n"
            "- evidence_summary (2 sentences max)\n"
        ),
        expected_output="JSON with risk_level, abuse_type, recommended_action, requires_human_approval, confidence, evidence_summary",
        agent=agent,
    )
