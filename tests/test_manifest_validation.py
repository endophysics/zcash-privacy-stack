from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.privacy_contract_types import ContractKind
from scripts.privacy_contract_validation import validate_document

from tests.privacy_json import IssueExpectation, assert_issue, manifest_document, write_document

if TYPE_CHECKING:
    from pathlib import Path


def test_manifest_requires_canonically_ordered_ranges(tmp_path: Path) -> None:
    document = manifest_document()
    document["objects"] = [
        {
            "kind": "compact_block_range",
            "id": "200-100",
            "start_height": 200,
            "end_height": 100,
            "sha256": "b" * 64,
            "bytes": 1024,
            "url": "objects/200-100.bin",
        }
    ]
    source = write_document(tmp_path, "manifest.json", document)

    report = validate_document(ContractKind.CANONICAL_READ_MANIFEST, source)

    assert_issue(
        report,
        IssueExpectation("manifest.range.order", ("objects", 0), (("earlier", "start_height"),)),
    )


def test_manifest_rejects_unsupported_major_version(tmp_path: Path) -> None:
    source = write_document(
        tmp_path,
        "manifest.json",
        {**manifest_document(), "format_version": "2.0.0"},
    )

    report = validate_document(ContractKind.CANONICAL_READ_MANIFEST, source)

    assert_issue(
        report,
        IssueExpectation("version.unsupported", ("format_version",), (("supported_major", "1"),)),
    )


def test_manifest_rejects_leading_zero_format_version(tmp_path: Path) -> None:
    source = write_document(
        tmp_path,
        "manifest.json",
        {**manifest_document(), "format_version": "01.0.0"},
    )

    report = validate_document(ContractKind.CANONICAL_READ_MANIFEST, source)

    assert_issue(
        report,
        IssueExpectation("schema.pattern", ("format_version",), (("pattern", "semver"),)),
    )


def test_manifest_enforces_uri_reference_format(tmp_path: Path) -> None:
    document = manifest_document()
    document["objects"] = [
        {
            "kind": "compact_block_range",
            "id": "100-200",
            "start_height": 100,
            "end_height": 200,
            "sha256": "b" * 64,
            "bytes": 1024,
            "url": "https:// bad uri",
        }
    ]
    source = write_document(tmp_path, "manifest.json", document)

    report = validate_document(ContractKind.CANONICAL_READ_MANIFEST, source)

    assert_issue(
        report,
        IssueExpectation("schema.format", ("objects", 0, "url"), (("format", "uri-reference"),)),
    )
