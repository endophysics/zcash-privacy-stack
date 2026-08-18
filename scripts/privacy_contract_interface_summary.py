"""Static offline interface-summary command implementation."""

from __future__ import annotations

import json
import sys
from typing import Final, TypedDict

from scripts.privacy_contract_semantics import SUPPORTED_MAJOR
from scripts.privacy_contract_types import ContractKind

CANONICAL_OBJECT_KINDS: Final = (
    "compact_block_range",
    "full_transaction_block",
    "full_transaction_range",
    "subtree_roots",
    "mempool_snapshot",
    "mempool_delta",
)


class ContractSummary(TypedDict):
    """One independently versioned JSON contract."""

    id: str
    version_field: str
    supported_major: int


class PrivateAdmissionVersion(TypedDict):
    """The independently versioned private-admission Protocol Buffers package."""

    package: str
    major: int
    status: str


class ConceptSummary(TypedDict):
    """Structured interface metadata for one cross-contract concept."""

    concept: str
    details: dict[str, str | bool | list[str]]


class InterfaceSummaryOutput(TypedDict):
    """Static machine-readable summary of the WP01 interface surface."""

    contracts: list[ContractSummary]
    versions: dict[str, PrivateAdmissionVersion]
    concepts: list[ConceptSummary]


def run_interface_summary() -> int:
    """Print static machine-readable metadata without reading prose documentation."""
    _ = sys.stdout.write(
        f"{json.dumps(_interface_summary_output(), sort_keys=True, separators=(',', ':'))}\n"
    )
    return 0


def _interface_summary_output() -> InterfaceSummaryOutput:
    return {
        "contracts": [
            {
                "id": ContractKind.PRIVACY_POLICY.value,
                "version_field": "policy_version",
                "supported_major": SUPPORTED_MAJOR,
            },
            {
                "id": ContractKind.PRIVACY_CAPABILITIES.value,
                "version_field": "capabilities_version",
                "supported_major": SUPPORTED_MAJOR,
            },
            {
                "id": ContractKind.CANONICAL_READ_MANIFEST.value,
                "version_field": "format_version",
                "supported_major": SUPPORTED_MAJOR,
            },
        ],
        "versions": {
            "private_admission": {
                "package": "zcash.privacy.admission.v1",
                "major": 1,
                "status": "unchanged",
            }
        },
        "concepts": [
            {
                "concept": "policy_security",
                "details": {
                    "private_write": "policy/private_write",
                    "read_privacy": "policy/read_privacy",
                    "unsupported_major": "fail_closed",
                },
            },
            {
                "concept": "capability_write_read",
                "details": {
                    "private_write": "capabilities/private_write",
                    "read_privacy": "capabilities/read_privacy",
                },
            },
            {
                "concept": "canonical_object_kinds",
                "details": {"kinds": list(CANONICAL_OBJECT_KINDS)},
            },
            {
                "concept": "freshness",
                "details": {
                    "enabled_by": "--check-freshness",
                    "at_value": "rfc3339_utc",
                    "default_enabled": False,
                },
            },
            {
                "concept": "additive_compatibility",
                "details": {
                    "optional_fields": "reader_ignores",
                    "incompatible_change": "new_major",
                },
            },
        ],
    }
