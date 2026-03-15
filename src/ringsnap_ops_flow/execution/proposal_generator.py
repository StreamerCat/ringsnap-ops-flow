"""Adapter to convert repo-aware diagnosis payloads into executable patch plans."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .workflows import FilePatch, PatchPlan


class ProposalGenerationError(ValueError):
    """Raised when a diagnosis payload cannot be converted into a patch plan."""


@dataclass(frozen=True)
class PatchProposal:
    plan: PatchPlan
    validation_class: str


def proposal_from_diagnosis_json(diagnosis_payload: str) -> PatchProposal:
    """Convert diagnosis JSON into a PatchProposal for RepoExecutionLane."""
    try:
        payload = json.loads(diagnosis_payload)
    except json.JSONDecodeError as exc:
        raise ProposalGenerationError("Diagnosis payload is not valid JSON") from exc

    change_class = payload.get("change_class", "")
    title = payload.get("title", "")
    summary = payload.get("summary", "")
    validation_class = payload.get("validation_class") or change_class
    scoped_files = payload.get("scoped_files", [])

    if not change_class:
        raise ProposalGenerationError("Diagnosis payload missing change_class")
    if not title:
        raise ProposalGenerationError("Diagnosis payload missing title")
    if not scoped_files:
        raise ProposalGenerationError("Diagnosis payload missing scoped_files")

    patches: list[FilePatch] = []
    for item in scoped_files:
        path = item.get("path", "")
        content = item.get("content", "")
        if not path:
            raise ProposalGenerationError("Scoped file entry missing path")
        patches.append(FilePatch(path=path, content=content))

    plan = PatchPlan(
        change_class=change_class,
        title=title,
        summary=summary or "Patch generated from repo-aware diagnosis.",
        patches=patches,
        base_branch=payload.get("base_branch", "main"),
        validation_class=validation_class,
    )
    return PatchProposal(plan=plan, validation_class=validation_class)
