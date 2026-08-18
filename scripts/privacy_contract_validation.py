"""Public orchestrator for offline privacy contract validation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypedDict

from scripts.privacy_contract_json import (
    JsonFileFailure,
    JsonFileFailureKind,
    load_json_document,
)
from scripts.privacy_contract_schema import load_schema, structural_issues
from scripts.privacy_contract_semantics import SemanticOptions, semantic_issues
from scripts.privacy_contract_types import (
    ContractKind,
    JsonLocation,
    MachineData,
    ValidationIssue,
    ValidationReport,
)

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


class RenderedIssue(TypedDict):
    """One JSON-safe validation issue."""

    code: str
    location: str
    data: dict[str, str]


class ValidationOutput(TypedDict):
    """The stable command representation of one validation report."""

    valid: bool
    kind: str
    source: str | None
    issues: list[RenderedIssue]


def validate_document(
    kind: ContractKind,
    path: Path,
    *,
    check_freshness: bool = False,
    at: datetime | None = None,
) -> ValidationReport:
    """Validate one contract against its local schema and semantic rules."""
    source = path.resolve()
    loaded = load_json_document(source)
    if isinstance(loaded, JsonFileFailure):
        issues = (_document_file_issue(loaded.kind, loaded.reason),)
    else:
        document = loaded
        schema = load_schema(kind)
        if isinstance(schema, ValidationIssue):
            issues = (schema,)
        else:
            issues = structural_issues(schema, document)
            if not issues:
                issues = semantic_issues(
                    kind,
                    document,
                    SemanticOptions(check_freshness=check_freshness, at=at),
                )
    return ValidationReport(kind=kind, source=source, issues=tuple(sorted(issues, key=_issue_key)))


def _document_file_issue(kind: JsonFileFailureKind, reason: str) -> ValidationIssue:
    if kind is JsonFileFailureKind.READ:
        return ValidationIssue("document.read", (), (("reason", reason),))
    return ValidationIssue("document.invalid", (), (("reason", reason),))


def _issue_key(
    issue: ValidationIssue,
) -> tuple[tuple[tuple[int, str], ...], str, MachineData]:
    return (
        tuple(_location_segment_key(segment) for segment in issue.location),
        issue.code,
        issue.data,
    )


def _location_segment_key(segment: str | int) -> tuple[int, str]:
    if isinstance(segment, str):
        return 0, segment
    return 1, str(segment).zfill(20)


def render_json_pointer(location: JsonLocation) -> str:
    """Render a JSON location as an RFC 6901 JSON Pointer."""
    return "".join(f"/{_escape_pointer_segment(segment)}" for segment in location)


def render_issue(issue: ValidationIssue) -> RenderedIssue:
    """Render one issue without flattening its machine-readable data."""
    return {
        "code": issue.code,
        "location": render_json_pointer(issue.location),
        "data": dict(issue.data),
    }


def render_validation_report(report: ValidationReport) -> ValidationOutput:
    """Render the complete validation outcome for a command response."""
    return {
        "valid": report.is_valid,
        "kind": report.kind.value,
        "source": str(report.source),
        "issues": [render_issue(issue) for issue in report.issues],
    }


def render_validation_error(kind: str, issue: ValidationIssue) -> ValidationOutput:
    """Render a command-input failure using the validation response shape."""
    return {
        "valid": False,
        "kind": kind,
        "source": None,
        "issues": [render_issue(issue)],
    }


def encode_json(document: ValidationOutput) -> str:
    """Encode a command response deterministically as one JSON document."""
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def _escape_pointer_segment(segment: str | int) -> str:
    text = str(segment)
    return text.replace("~", "~0").replace("/", "~1")
