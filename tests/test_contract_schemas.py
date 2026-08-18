from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate
from scripts.privacy_contract_types import ContractKind
from scripts.privacy_contract_validation import validate_document

from tests.privacy_json import (
    JsonDocument,
    load_json_document,
    policy_document,
    private_write_document,
    read_privacy_document,
)

PROJECT_ROOT: Final = Path(__file__).parents[1]
INTERFACES_ROOT: Final = PROJECT_ROOT / "interfaces"
EXAMPLES_ROOT: Final = PROJECT_ROOT / "examples"
SCHEMAS: Final = (
    (ContractKind.PRIVACY_POLICY, INTERFACES_ROOT / "privacy-policy.schema.json"),
    (ContractKind.PRIVACY_CAPABILITIES, INTERFACES_ROOT / "privacy-capabilities.schema.json"),
    (ContractKind.CANONICAL_READ_MANIFEST, INTERFACES_ROOT / "canonical-read-manifest.schema.json"),
)
EXAMPLES: Final = (
    (ContractKind.PRIVACY_POLICY, EXAMPLES_ROOT / "privacy-policy-v1.json"),
    (ContractKind.PRIVACY_CAPABILITIES, EXAMPLES_ROOT / "privacy-capabilities-v1.json"),
    (ContractKind.CANONICAL_READ_MANIFEST, EXAMPLES_ROOT / "canonical-read-manifest-v1.json"),
)


def test_schemas_are_draft_2020_12_self_consistent() -> None:
    for _, schema_path in SCHEMAS:
        assert schema_path.exists()
        schema = load_json_document(schema_path)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(schema)


def test_schema_ids_match_stable_major_one_urn_contract_ids() -> None:
    for kind, schema_path in SCHEMAS:
        assert schema_path.exists()
        schema = load_json_document(schema_path)
        assert schema["$id"] == kind.value


def test_all_contract_examples_are_parseable_json_objects() -> None:
    for _, example_path in EXAMPLES:
        assert example_path.is_file()
        _ = load_json_document(example_path)


@pytest.mark.parametrize(
    "document",
    [
        {
            **policy_document(),
            "private_write": {**private_write_document(), "direct_fallback_allowed": True},
        },
        {
            **policy_document(),
            "read_privacy": {**read_privacy_document(), "separate_write_session": False},
        },
        {
            **policy_document(),
            "read_privacy": {
                **read_privacy_document(),
                "transaction_specific_queries_allowed": True,
            },
        },
        {
            **policy_document(),
            "private_write": {**private_write_document(), "padding_bytes": 1023},
        },
        {
            **policy_document(),
            "private_write": {**private_write_document(), "padding_bytes": 1_048_577},
        },
    ],
)
def test_policy_schema_rejects_fail_closed_and_padding_regressions(
    document: JsonDocument,
) -> None:
    schema = load_json_document(INTERFACES_ROOT / "privacy-policy.schema.json")

    with pytest.raises(ValidationError):
        validate(document, schema, cls=Draft202012Validator)


def test_each_contract_example_validates_with_its_declared_kind() -> None:
    for kind, example_path in EXAMPLES:
        assert example_path.is_file()

        report = validate_document(kind, example_path)

        assert report.kind is kind
        assert report.source == example_path
        assert report.is_valid
