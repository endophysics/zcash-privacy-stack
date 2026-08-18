"""Offline policy-example command implementation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final, TypedDict

from scripts.privacy_contract_json import JsonFileFailure, load_json_document
from scripts.privacy_contract_types import ContractKind, ValidationIssue
from scripts.privacy_contract_validation import encode_json, render_validation_error

if TYPE_CHECKING:
    from scripts.privacy_contract_json import JsonDocument


POLICY_EXAMPLE_PATH: Final = (
    Path(__file__).resolve().parents[1] / "examples" / "privacy-policy-v1.json"
)


class PolicyExplanation(TypedDict):
    """A machine-readable explanation of one example policy setting."""

    concept: str
    pointer: str
    meaning: str


class PolicyExampleOutput(TypedDict):
    """The exact policy example plus its structured explanations."""

    policy: JsonDocument
    explanations: list[PolicyExplanation]


def run_policy_example() -> int:
    """Print the exact local policy example with structured explanations."""
    loaded = load_json_document(POLICY_EXAMPLE_PATH)
    if isinstance(loaded, JsonFileFailure):
        issue = ValidationIssue("example.unavailable", (), (("reason", loaded.reason),))
        rendered = encode_json(render_validation_error(ContractKind.PRIVACY_POLICY.value, issue))
        _ = sys.stderr.write(f"{rendered}\n")
        return 1
    rendered = json.dumps(_policy_example_output(loaded), sort_keys=True, separators=(",", ":"))
    _ = sys.stdout.write(f"{rendered}\n")
    return 0


def _policy_example_output(policy: JsonDocument) -> PolicyExampleOutput:
    return {
        "policy": policy,
        "explanations": [
            {
                "concept": "batching",
                "pointer": "/private_write/release_mode",
                "meaning": "fixed_epoch_release",
            },
            {
                "concept": "padding",
                "pointer": "/private_write/padding_bytes",
                "meaning": "minimum_padded_bytes",
            },
            {
                "concept": "relay",
                "pointer": "/private_write/relay_set_id",
                "meaning": "shared_relay_set",
            },
            {
                "concept": "attestation",
                "pointer": "/private_write/attestation_required",
                "meaning": "attestation_bundle_required",
            },
            {
                "concept": "canonical_reads",
                "pointer": "/read_privacy/canonical_objects",
                "meaning": "canonical_manifest_required",
            },
            {
                "concept": "fail_closed_fallback",
                "pointer": "/private_write/direct_fallback_allowed",
                "meaning": "direct_fallback_disabled",
            },
        ],
    }
