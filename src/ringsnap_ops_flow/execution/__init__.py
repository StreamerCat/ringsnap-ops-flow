"""Execution lane package for safe patch+PR workflows."""

from .policy import AutonomyPolicy
from .validator import TargetedValidator
from .proposal_generator import PatchProposal, ProposalGenerationError, proposal_from_diagnosis_json
from .workflows import (
    RepoExecutionLane,
    PatchPlan,
    FilePatch,
    ExecutionOutcome,
    build_low_risk_marketing_plan,
    build_activation_failure_pr_only_plan,
)

__all__ = [
    "AutonomyPolicy",
    "TargetedValidator",
    "RepoExecutionLane",
    "PatchPlan",
    "FilePatch",
    "ExecutionOutcome",
    "build_low_risk_marketing_plan",
    "build_activation_failure_pr_only_plan",
    "PatchProposal",
    "ProposalGenerationError",
    "proposal_from_diagnosis_json",
]
