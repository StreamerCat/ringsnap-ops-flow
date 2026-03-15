"""Tests for diagnosis-to-patch proposal conversion."""

import pytest

from ringsnap_ops_flow.execution.proposal_generator import (
    ProposalGenerationError,
    proposal_from_diagnosis_json,
)


def test_proposal_generator_maps_fields_into_patch_plan():
    diagnosis_json = """
    {
      "change_class": "seo_meta_schema",
      "validation_class": "marketing_lighthouse",
      "title": "fix(marketing): tune metadata",
      "summary": "Use repo evidence to update metadata.",
      "base_branch": "main",
      "scoped_files": [
        {"path": "docs/runbooks/incident.md", "content": "updated"}
      ]
    }
    """

    proposal = proposal_from_diagnosis_json(diagnosis_json)
    assert proposal.plan.change_class == "seo_meta_schema"
    assert proposal.validation_class == "marketing_lighthouse"
    assert proposal.plan.validation_class == "marketing_lighthouse"
    assert proposal.plan.patches[0].path == "docs/runbooks/incident.md"


def test_proposal_generator_requires_scoped_files():
    diagnosis_json = '{"change_class":"seo_meta_schema","title":"t","summary":"s","scoped_files":[]}'
    with pytest.raises(ProposalGenerationError, match="scoped_files"):
        proposal_from_diagnosis_json(diagnosis_json)
