from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, TypeAlias

from pydantic import JsonValue, TypeAdapter

if TYPE_CHECKING:
    from pathlib import Path

    from scripts.privacy_contract_types import JsonLocation, MachineData, ValidationReport


JsonDocument: TypeAlias = dict[str, JsonValue]
JSON_DOCUMENT_ADAPTER: Final = TypeAdapter(JsonDocument)


def parse_json_document(content: str | bytes) -> JsonDocument:
    return JSON_DOCUMENT_ADAPTER.validate_json(content)


def load_json_document(path: Path) -> JsonDocument:
    return parse_json_document(path.read_bytes())


@dataclass(frozen=True, slots=True)
class IssueExpectation:
    code: str
    location: JsonLocation
    data: MachineData


def write_document(tmp_path: Path, name: str, document: JsonDocument) -> Path:
    path = tmp_path / name
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    return path


def node_document() -> JsonDocument:
    return {
        "implementation": "zakura",
        "revision": "0123456789abcdef",
        "fixed_logical_egress": False,
    }


def private_write_document() -> JsonDocument:
    return {
        "enabled": False,
        "submission_protocol": "ohttp-zcash-tx-v1",
        "padding_bytes": 1024,
        "minimum_delay_ms": 10,
        "maximum_delay_ms": 20,
        "epoch_ms": 60_000,
        "release_mode": "fixed_epoch",
        "relay_set_id": "local-relay-set",
        "gateway_key_id": "local-gateway-key",
        "attestation_required": False,
        "direct_fallback_allowed": False,
    }


def read_privacy_document() -> JsonDocument:
    return {
        "range_bucket_size": 100,
        "lookback_blocks": 200,
        "poll_interval_ms": 1_000,
        "mempool_epoch_ms": 60_000,
        "separate_write_session": True,
        "canonical_objects": False,
        "transaction_specific_queries_allowed": False,
        "transparent_local_scan": False,
    }


def policy_document(
    private_write: JsonDocument | None = None,
    node: JsonDocument | None = None,
    read_privacy: JsonDocument | None = None,
) -> JsonDocument:
    return {
        "policy_version": "1.0.0",
        "service_id": "local-policy-test",
        "network": "testnet",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2026-12-31T00:00:00Z",
        "node": node if node is not None else node_document(),
        "private_write": private_write if private_write is not None else private_write_document(),
        "read_privacy": read_privacy if read_privacy is not None else read_privacy_document(),
    }


def capabilities_node_document() -> JsonDocument:
    return {
        "implementation": "zakura",
        "revision": "0123456789abcdef",
    }


def capabilities_attestation_document() -> JsonDocument:
    return {
        "supported": True,
        "required": False,
    }


def capabilities_private_write_document(
    attestation: JsonDocument | None = None,
) -> JsonDocument:
    return {
        "enabled": False,
        "submission_protocols": ["ohttp-zcash-tx-v1"],
        "release_modes": ["fixed_epoch"],
        "maximum_transaction_bytes": 1_000_000,
        "attestation": attestation
        if attestation is not None
        else capabilities_attestation_document(),
    }


def range_bucketing_document() -> JsonDocument:
    return {
        "supported": True,
        "bucket_sizes": [100],
    }


def canonical_objects_document() -> JsonDocument:
    return {"supported": True}


def mempool_epochs_document() -> JsonDocument:
    return {
        "supported": True,
        "epoch_ms": 60_000,
    }


def capabilities_read_privacy_document(
    range_bucketing: JsonDocument | None = None,
    canonical_objects: JsonDocument | None = None,
    mempool_epochs: JsonDocument | None = None,
) -> JsonDocument:
    return {
        "range_bucketing": range_bucketing
        if range_bucketing is not None
        else range_bucketing_document(),
        "canonical_objects": (
            canonical_objects if canonical_objects is not None else canonical_objects_document()
        ),
        "mempool_epochs": mempool_epochs
        if mempool_epochs is not None
        else mempool_epochs_document(),
        "separate_write_session": True,
        "transparent_local_scan": False,
    }


def capabilities_document(
    node: JsonDocument | None = None,
    private_write: JsonDocument | None = None,
    read_privacy: JsonDocument | None = None,
) -> JsonDocument:
    return {
        "capabilities_version": "1.0.0",
        "service_id": "local-capabilities-test",
        "network": "testnet",
        "node": node if node is not None else capabilities_node_document(),
        "supported_policy_versions": ["1.0.0"],
        "private_write": (
            private_write if private_write is not None else capabilities_private_write_document()
        ),
        "read_privacy": (
            read_privacy if read_privacy is not None else capabilities_read_privacy_document()
        ),
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2026-12-31T00:00:00Z",
    }


def manifest_document() -> JsonDocument:
    return {
        "format_version": "1.0.0",
        "network": "testnet",
        "generation": 1,
        "generated_at": "2026-06-01T00:00:00Z",
        "chain_tip_height": 200,
        "chain_tip_hash": "a" * 64,
        "objects": [
            {
                "kind": "compact_block_range",
                "id": "100-200",
                "start_height": 100,
                "end_height": 200,
                "sha256": "b" * 64,
                "bytes": 1024,
                "url": "objects/100-200.bin",
            }
        ],
    }


def assert_issue(report: ValidationReport, expected: IssueExpectation) -> None:
    assert not report.is_valid
    assert report.issues
    issue = report.issues[0]
    assert issue.code == expected.code
    assert issue.location == expected.location
    assert issue.data == expected.data
