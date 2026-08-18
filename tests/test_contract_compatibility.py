from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from scripts.privacy_contract_types import ContractKind
from scripts.privacy_contract_validation import validate_document

from tests.privacy_json import (
    IssueExpectation,
    assert_issue,
    policy_document,
    private_write_document,
    write_document,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_policy_accepts_unknown_root_and_nested_additive_fields(tmp_path: Path) -> None:
    document = policy_document()
    document["future_root"] = {"revision": 2}
    document["node"] = {
        "implementation": "zakura",
        "revision": "0123456789abcdef",
        "fixed_logical_egress": False,
        "future_node": True,
    }
    source = write_document(tmp_path, "policy.json", document)

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert report.is_valid


@pytest.mark.parametrize("version", ["version-one", "2.0.0"])
def test_policy_rejects_malformed_and_unsupported_versions(tmp_path: Path, version: str) -> None:
    source = write_document(
        tmp_path, "policy.json", {**policy_document(), "policy_version": version}
    )

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    expected = (
        IssueExpectation("schema.pattern", ("policy_version",), (("pattern", "semver"),))
        if version == "version-one"
        else IssueExpectation(
            "version.unsupported", ("policy_version",), (("supported_major", "1"),)
        )
    )
    assert_issue(report, expected)


def test_policy_rejects_leading_zero_version(tmp_path: Path) -> None:
    source = write_document(
        tmp_path, "policy.json", {**policy_document(), "policy_version": "01.0.0"}
    )

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation("schema.pattern", ("policy_version",), (("pattern", "semver"),)),
    )


def test_policy_requires_ordered_validity_window(tmp_path: Path) -> None:
    source = write_document(
        tmp_path,
        "policy.json",
        {
            **policy_document(),
            "valid_from": "2026-12-31T00:00:00Z",
            "valid_until": "2026-01-01T00:00:00Z",
        },
    )

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report, IssueExpectation("policy.validity.order", (), (("earlier", "valid_from"),))
    )


def test_policy_checks_freshness_at_a_fixed_epoch(tmp_path: Path) -> None:
    source = write_document(tmp_path, "policy.json", policy_document())

    report = validate_document(
        ContractKind.PRIVACY_POLICY,
        source,
        check_freshness=True,
        at=datetime(2027, 1, 1, tzinfo=UTC),
    )

    assert_issue(
        report,
        IssueExpectation("policy.validity.expired", (), (("at", "2027-01-01T00:00:00+00:00"),)),
    )


def test_policy_requires_ordered_private_write_delays(tmp_path: Path) -> None:
    private_write = private_write_document()
    private_write["minimum_delay_ms"] = 21
    private_write["maximum_delay_ms"] = 20
    source = write_document(tmp_path, "policy.json", policy_document(private_write=private_write))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation(
            "policy.delay.order", ("private_write",), (("earlier", "minimum_delay_ms"),)
        ),
    )


def test_policy_limits_enabled_development_direct_to_development_nodes(tmp_path: Path) -> None:
    private_write = private_write_document()
    private_write["enabled"] = True
    private_write["submission_protocol"] = "development-direct-v1"
    source = write_document(tmp_path, "policy.json", policy_document(private_write=private_write))

    report = validate_document(ContractKind.PRIVACY_POLICY, source)

    assert_issue(
        report,
        IssueExpectation(
            "policy.development_direct.requires_development_node",
            ("private_write", "submission_protocol"),
            (("implementation", "zakura"),),
        ),
    )
