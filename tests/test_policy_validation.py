from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import pytest
from scripts.privacy_contract_types import ContractKind, JsonLocation
from scripts.privacy_contract_validation import validate_document

from tests.privacy_json import (
    IssueExpectation,
    assert_issue,
    node_document,
    policy_document,
    private_write_document,
    read_privacy_document,
    write_document,
)

if TYPE_CHECKING:
    from pathlib import Path

FIXED_NOW: Final = datetime(2026, 6, 1, tzinfo=UTC)


def test_policy_allows_explicit_false_security_switches(tmp_path: Path) -> None:
    source = write_document(tmp_path, "policy.json", policy_document())

    report = validate_document(
        ContractKind.PRIVACY_POLICY, source, check_freshness=True, at=FIXED_NOW
    )

    assert report.kind is ContractKind.PRIVACY_POLICY
    assert report.source == source
    assert report.is_valid


@pytest.mark.parametrize("section", ["node", "private_write", "read_privacy", "valid_until"])
def test_policy_requires_security_sections_and_expiry(tmp_path: Path, section: str) -> None:
    document = policy_document()
    del document[section]
    source = write_document(tmp_path, "policy.json", document)

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(report, IssueExpectation("schema.required", (section,), (("field", section),)))


@pytest.mark.parametrize(
    "field",
    [
        "enabled",
        "submission_protocol",
        "padding_bytes",
        "minimum_delay_ms",
        "maximum_delay_ms",
        "release_mode",
        "relay_set_id",
        "gateway_key_id",
        "attestation_required",
        "direct_fallback_allowed",
    ],
)
def test_policy_requires_private_write_security_fields(tmp_path: Path, field: str) -> None:
    private_write = private_write_document()
    del private_write[field]
    source = write_document(tmp_path, "policy.json", policy_document(private_write=private_write))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation("schema.required", ("private_write", field), (("field", field),)),
    )


def test_policy_requires_explicit_fixed_logical_egress_switch(tmp_path: Path) -> None:
    node = node_document()
    del node["fixed_logical_egress"]
    source = write_document(tmp_path, "policy.json", policy_document(node=node))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation(
            "schema.required",
            ("node", "fixed_logical_egress"),
            (("field", "fixed_logical_egress"),),
        ),
    )


@pytest.mark.parametrize(
    "field",
    [
        "range_bucket_size",
        "lookback_blocks",
        "poll_interval_ms",
        "mempool_epoch_ms",
        "separate_write_session",
        "canonical_objects",
        "transaction_specific_queries_allowed",
        "transparent_local_scan",
    ],
)
def test_policy_requires_read_privacy_fields(tmp_path: Path, field: str) -> None:
    read_privacy = read_privacy_document()
    del read_privacy[field]
    source = write_document(tmp_path, "policy.json", policy_document(read_privacy=read_privacy))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation(
            "schema.required",
            ("read_privacy", field),
            (("field", field),),
        ),
    )


def test_policy_requires_epoch_for_fixed_epoch_release(tmp_path: Path) -> None:
    private_write = private_write_document()
    del private_write["epoch_ms"]
    source = write_document(tmp_path, "policy.json", policy_document(private_write=private_write))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation("policy.fixed_epoch.requires_epoch_ms", ("private_write",), ()),
    )


def test_policy_requires_attestation_bundle_when_attestation_is_enabled(tmp_path: Path) -> None:
    private_write = private_write_document()
    private_write["attestation_required"] = True
    source = write_document(tmp_path, "policy.json", policy_document(private_write=private_write))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation(
            "policy.attestation.requires_bundle_url", (), (("field", "attestation_bundle_url"),)
        ),
    )


def test_policy_requires_manifest_when_canonical_reads_are_enabled(tmp_path: Path) -> None:
    read_privacy = read_privacy_document()
    read_privacy["canonical_objects"] = True
    source = write_document(tmp_path, "policy.json", policy_document(read_privacy=read_privacy))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation(
            "policy.canonical_reads.requires_manifest_url",
            (),
            (("field", "canonical_manifest_url"),),
        ),
    )


@pytest.mark.parametrize(
    ("field", "value", "location", "format_name"),
    [
        ("valid_from", "not-a-date", ("valid_from",), "rfc3339"),
        ("attestation_bundle_url", "not a uri", ("attestation_bundle_url",), "uri"),
    ],
)
def test_policy_enforces_strict_date_and_uri_formats(
    tmp_path: Path,
    field: str,
    value: str,
    location: JsonLocation,
    format_name: str,
) -> None:
    document = {**policy_document(), field: value}
    source = write_document(tmp_path, "policy.json", document)

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(report, IssueExpectation("schema.format", location, (("format", format_name),)))
