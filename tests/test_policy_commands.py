from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final

from scripts.privacy_contract_types import ValidationIssue
from scripts.privacy_contract_validation import render_issue

from tests.privacy_json import parse_json_document, policy_document, write_document

PROJECT_ROOT: Final = Path(__file__).parents[1]
POLICY_EXAMPLE: Final = PROJECT_ROOT / "scripts" / "policy-example"
POLICY_VALIDATE: Final = PROJECT_ROOT / "scripts" / "policy-validate"
INTERFACE_SUMMARY: Final = PROJECT_ROOT / "scripts" / "interface-summary"


def run_command(command: Path, arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(command), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_policy_example_outputs_policy_and_structured_explanations() -> None:
    assert POLICY_EXAMPLE.exists()

    completed = run_command(POLICY_EXAMPLE, ())

    output = parse_json_document(completed.stdout)
    assert completed.returncode == 0
    assert output["policy"] == parse_json_document(
        (PROJECT_ROOT / "examples" / "privacy-policy-v1.json").read_bytes()
    )
    explanations = output["explanations"]
    assert isinstance(explanations, list)
    assert {
        str(explanation["concept"]) for explanation in explanations if isinstance(explanation, dict)
    } == {
        "batching",
        "padding",
        "relay",
        "attestation",
        "canonical_reads",
        "fail_closed_fallback",
    }
    assert {
        str(explanation["concept"]): str(explanation["pointer"])
        for explanation in explanations
        if isinstance(explanation, dict)
    } == {
        "batching": "/private_write/release_mode",
        "padding": "/private_write/padding_bytes",
        "relay": "/private_write/relay_set_id",
        "attestation": "/private_write/attestation_required",
        "canonical_reads": "/read_privacy/canonical_objects",
        "fail_closed_fallback": "/private_write/direct_fallback_allowed",
    }
    assert all(
        set(explanation) == {"concept", "pointer", "meaning"}
        for explanation in explanations
        if isinstance(explanation, dict)
    )
    assert "Traceback" not in completed.stderr


def test_policy_validate_outputs_structured_success_for_a_fresh_policy(tmp_path: Path) -> None:
    source = write_document(tmp_path, "policy.json", policy_document())
    assert POLICY_VALIDATE.exists()

    completed = run_command(
        POLICY_VALIDATE,
        ("--check-freshness", "--at", "2026-06-01T00:00:00Z", str(source)),
    )

    output = parse_json_document(completed.stdout)
    assert completed.returncode == 0
    assert output["valid"] is True
    assert output["issues"] == []
    assert "Traceback" not in completed.stderr


def test_policy_validate_outputs_structured_stderr_for_a_missing_policy(tmp_path: Path) -> None:
    missing = tmp_path / "missing-policy.json"
    assert POLICY_VALIDATE.exists()

    completed = run_command(POLICY_VALIDATE, (str(missing),))

    error = parse_json_document(completed.stderr)
    assert completed.returncode == 1
    assert error["valid"] is False
    assert error["issues"]
    assert "Traceback" not in completed.stderr


def test_policy_validate_rejects_at_without_freshness(tmp_path: Path) -> None:
    source = write_document(tmp_path, "policy.json", policy_document())

    completed = run_command(POLICY_VALIDATE, ("--at", "2026-06-01T00:00:00Z", str(source)))

    error = parse_json_document(completed.stderr)
    assert completed.returncode == 1
    assert error["valid"] is False
    assert error["issues"] == [
        {
            "code": "argument.at_requires_freshness",
            "location": "",
            "data": {"option": "--at"},
        }
    ]
    assert "Traceback" not in completed.stderr


def test_issue_renderer_uses_rfc6901_escaped_pointers_and_structured_data() -> None:
    rendered = render_issue(
        ValidationIssue(
            code="example.constraint",
            location=("field/with/slash", "field~with~tilde", 2),
            data=(("constraint", "example"),),
        )
    )

    assert rendered == {
        "code": "example.constraint",
        "location": "/field~1with~1slash/field~0with~0tilde/2",
        "data": {"constraint": "example"},
    }


def test_interface_summary_outputs_contract_version_and_concept_data() -> None:
    assert INTERFACE_SUMMARY.exists()

    completed = run_command(INTERFACE_SUMMARY, ())

    output = parse_json_document(completed.stdout)
    assert completed.returncode == 0
    assert output["contracts"] == [
        {
            "id": "urn:zcash:privacy-stack:privacy-policy:1",
            "version_field": "policy_version",
            "supported_major": 1,
        },
        {
            "id": "urn:zcash:privacy-stack:privacy-capabilities:1",
            "version_field": "capabilities_version",
            "supported_major": 1,
        },
        {
            "id": "urn:zcash:privacy-stack:canonical-read-manifest:1",
            "version_field": "format_version",
            "supported_major": 1,
        },
    ]
    assert output["versions"] == {
        "private_admission": {
            "package": "zcash.privacy.admission.v1",
            "major": 1,
            "status": "unchanged",
        }
    }
    concepts = output["concepts"]
    assert isinstance(concepts, list)
    assert {str(concept["concept"]) for concept in concepts if isinstance(concept, dict)} == {
        "policy_security",
        "capability_write_read",
        "canonical_object_kinds",
        "freshness",
        "additive_compatibility",
    }
    assert "Traceback" not in completed.stderr
