from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from scripts.privacy_contract_types import ContractKind
from scripts.privacy_contract_validation import validate_document

from tests.privacy_json import (
    IssueExpectation,
    assert_issue,
    canonical_objects_document,
    capabilities_attestation_document,
    capabilities_document,
    capabilities_node_document,
    capabilities_private_write_document,
    capabilities_read_privacy_document,
    mempool_epochs_document,
    range_bucketing_document,
    write_document,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "field",
    [
        "capabilities_version",
        "service_id",
        "network",
        "node",
        "supported_policy_versions",
        "private_write",
        "read_privacy",
        "valid_from",
        "valid_until",
    ],
)
def test_capabilities_require_root_discovery_fields(tmp_path: Path, field: str) -> None:
    document = capabilities_document()
    del document[field]
    source = write_document(tmp_path, "capabilities.json", document)

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(report, IssueExpectation("schema.required", (field,), (("field", field),)))


@pytest.mark.parametrize("field", ["implementation", "revision"])
def test_capabilities_require_node_identity_fields(tmp_path: Path, field: str) -> None:
    node = capabilities_node_document()
    del node[field]
    source = write_document(tmp_path, "capabilities.json", capabilities_document(node=node))

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(report, IssueExpectation("schema.required", ("node", field), (("field", field),)))


@pytest.mark.parametrize(
    "field",
    [
        "enabled",
        "submission_protocols",
        "release_modes",
        "maximum_transaction_bytes",
        "attestation",
    ],
)
def test_capabilities_require_private_write_fields(tmp_path: Path, field: str) -> None:
    private_write = capabilities_private_write_document()
    del private_write[field]
    source = write_document(
        tmp_path,
        "capabilities.json",
        capabilities_document(private_write=private_write),
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation("schema.required", ("private_write", field), (("field", field),)),
    )


@pytest.mark.parametrize("field", ["submission_protocols", "release_modes"])
def test_capabilities_require_nonempty_private_write_concepts(tmp_path: Path, field: str) -> None:
    private_write = capabilities_private_write_document()
    private_write[field] = []
    source = write_document(
        tmp_path,
        "capabilities.json",
        capabilities_document(private_write=private_write),
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation("schema.min_items", ("private_write", field), (("minimum", "1"),)),
    )


@pytest.mark.parametrize("field", ["supported", "required"])
def test_capabilities_require_attestation_fields(tmp_path: Path, field: str) -> None:
    attestation = capabilities_attestation_document()
    del attestation[field]
    private_write = capabilities_private_write_document(attestation=attestation)
    source = write_document(
        tmp_path,
        "capabilities.json",
        capabilities_document(private_write=private_write),
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation(
            "schema.required",
            ("private_write", "attestation", field),
            (("field", field),),
        ),
    )


@pytest.mark.parametrize(
    "field",
    [
        "range_bucketing",
        "canonical_objects",
        "mempool_epochs",
        "separate_write_session",
        "transparent_local_scan",
    ],
)
def test_capabilities_require_read_privacy_fields(tmp_path: Path, field: str) -> None:
    read_privacy = capabilities_read_privacy_document()
    del read_privacy[field]
    source = write_document(
        tmp_path,
        "capabilities.json",
        capabilities_document(read_privacy=read_privacy),
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation("schema.required", ("read_privacy", field), (("field", field),)),
    )


@pytest.mark.parametrize("field", ["supported", "bucket_sizes"])
def test_capabilities_require_range_bucketing_fields(tmp_path: Path, field: str) -> None:
    range_bucketing = range_bucketing_document()
    del range_bucketing[field]
    read_privacy = capabilities_read_privacy_document(range_bucketing=range_bucketing)
    source = write_document(
        tmp_path,
        "capabilities.json",
        capabilities_document(read_privacy=read_privacy),
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation(
            "schema.required",
            ("read_privacy", "range_bucketing", field),
            (("field", field),),
        ),
    )


def test_capabilities_require_canonical_object_support(tmp_path: Path) -> None:
    canonical_objects = canonical_objects_document()
    del canonical_objects["supported"]
    read_privacy = capabilities_read_privacy_document(canonical_objects=canonical_objects)
    source = write_document(
        tmp_path,
        "capabilities.json",
        capabilities_document(read_privacy=read_privacy),
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation(
            "schema.required",
            ("read_privacy", "canonical_objects", "supported"),
            (("field", "supported"),),
        ),
    )


@pytest.mark.parametrize("field", ["supported", "epoch_ms"])
def test_capabilities_require_mempool_epoch_fields(tmp_path: Path, field: str) -> None:
    mempool_epochs = mempool_epochs_document()
    del mempool_epochs[field]
    read_privacy = capabilities_read_privacy_document(mempool_epochs=mempool_epochs)
    source = write_document(
        tmp_path,
        "capabilities.json",
        capabilities_document(read_privacy=read_privacy),
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation(
            "schema.required",
            ("read_privacy", "mempool_epochs", field),
            (("field", field),),
        ),
    )


def test_capabilities_reject_unsupported_major_version(tmp_path: Path) -> None:
    source = write_document(
        tmp_path,
        "capabilities.json",
        {**capabilities_document(), "capabilities_version": "2.0.0"},
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation(
            "version.unsupported", ("capabilities_version",), (("supported_major", "1"),)
        ),
    )


def test_capabilities_reject_leading_zero_version(tmp_path: Path) -> None:
    source = write_document(
        tmp_path,
        "capabilities.json",
        {**capabilities_document(), "capabilities_version": "01.0.0"},
    )

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation("schema.pattern", ("capabilities_version",), (("pattern", "semver"),)),
    )


def test_capabilities_reject_leading_zero_supported_policy_version(tmp_path: Path) -> None:
    document = capabilities_document()
    document["supported_policy_versions"] = ["01.0.0"]
    source = write_document(tmp_path, "capabilities.json", document)

    report = validate_document(ContractKind.PRIVACY_CAPABILITIES, source)

    assert_issue(
        report,
        IssueExpectation(
            "schema.pattern",
            ("supported_policy_versions", 0),
            (("pattern", "semver"),),
        ),
    )
