from __future__ import annotations

import json
from pathlib import Path
from typing import Final, TypeAlias

import pytest
from jsonschema import Draft202012Validator, validate
from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import JsonValue, ValidationError
from scripts.wp06_legacy_client_contract import (
    CheckCode,
    CheckRecord,
    CheckStatus,
    Client,
    EvidenceGrade,
    Execution,
    LegacyClientResult,
    RolloutClassification,
    Scenario,
    TimelineEventCode,
    TimelineRecord,
)

from tests.privacy_json import load_json_document

Payload: TypeAlias = dict[str, JsonValue]
PythonPayloadValue: TypeAlias = JsonValue | tuple[CheckRecord, ...] | tuple[TimelineRecord, ...]
PythonPayload: TypeAlias = dict[str, PythonPayloadValue]

PROJECT_ROOT: Final = Path(__file__).parents[1]
SCHEMA_PATH: Final = PROJECT_ROOT / "interfaces" / "wp06-legacy-client-result.schema.json"
SCHEMA: Final = load_json_document(SCHEMA_PATH)
PROHIBITED_FIELDS: Final = (
    "transaction_id",
    "admission_id",
    "account_id",
    "endpoint_url",
    "endpoint_path",
    "checkout_path",
    "diagnostic",
    "error_message",
    "stderr",
    "timestamp",
    "elapsed",
    "latency",
    "duration",
    "credential",
    "raw_response",
)


def complete_payload() -> Payload:
    return {
        "format_version": 1,
        "client": "vizor",
        "client_release": "1.2.3",
        "scenario": "exact_retry",
        "evidence_grade": "local_rust_unit",
        "execution": "complete",
        "rollout_classification": "ordinary_immediate_endpoint",
        "checks": [{"code": "client_behavior", "status": "pass"}],
        "timeline": [{"code": "submission_call"}],
    }


def complete_python_payload() -> PythonPayload:
    return {
        "format_version": 1,
        "client": Client.VIZOR,
        "client_release": "1.2.3",
        "scenario": Scenario.EXACT_RETRY,
        "evidence_grade": EvidenceGrade.LOCAL_RUST_UNIT,
        "execution": Execution.COMPLETE,
        "rollout_classification": RolloutClassification.ORDINARY_IMMEDIATE_ENDPOINT,
        "checks": (CheckRecord(code=CheckCode.CLIENT_BEHAVIOR, status=CheckStatus.PASS),),
        "timeline": (TimelineRecord(code=TimelineEventCode.SUBMISSION_CALL),),
    }


def unavailable_payload() -> Payload:
    return {
        **complete_payload(),
        "evidence_grade": "local_flutter_unavailable",
        "execution": "unavailable",
        "rollout_classification": "inconclusive",
        "checks": [{"code": "client_behavior", "status": "not_run"}],
        "timeline": [],
        "unavailable_reason": "flutter_toolchain_unavailable",
    }


def accepts_with_pydantic(payload: Payload) -> bool:
    try:
        _ = LegacyClientResult.model_validate_json(json.dumps(payload))
    except ValidationError:
        return False
    return True


def accepts_with_schema(payload: Payload) -> bool:
    try:
        validate(payload, SCHEMA, cls=Draft202012Validator)
    except JsonSchemaValidationError:
        return False
    return True


def assert_parity(payload: Payload, *, expected: bool) -> None:
    pydantic_accepts = accepts_with_pydantic(payload)
    schema_accepts = accepts_with_schema(payload)

    assert pydantic_accepts is expected
    assert schema_accepts is expected


@pytest.mark.parametrize(
    "payload",
    [
        complete_payload(),
        {**complete_payload(), "unavailable_reason": None},
        unavailable_payload(),
        {
            **complete_payload(),
            "evidence_grade": "integrated_empirical",
            "rollout_classification": "private_endpoint_only",
        },
    ],
)
def test_checked_schema_accepts_every_valid_semantic_boundary(payload: Payload) -> None:
    assert_parity(payload, expected=True)


@pytest.mark.parametrize(
    "payload",
    [
        {**complete_payload(), "checks": []},
        {key: value for key, value in unavailable_payload().items() if key != "unavailable_reason"},
        {**unavailable_payload(), "unavailable_reason": None},
        {**unavailable_payload(), "checks": [{"code": "client_behavior", "status": "pass"}]},
        {**unavailable_payload(), "checks": [{"code": "client_behavior", "status": "fail"}]},
        {
            **unavailable_payload(),
            "checks": [
                {"code": "client_behavior", "status": "not_run"},
                {"code": "status_polling", "status": "pass"},
            ],
        },
        {**unavailable_payload(), "timeline": [{"code": "submission_call"}]},
        {**unavailable_payload(), "unavailable_reason": "arbitrary_diagnostic"},
        {**complete_payload(), "unavailable_reason": "cargo_unavailable"},
        {**complete_payload(), "evidence_grade": "local_flutter_unavailable"},
        {**complete_payload(), "evidence_grade": "unavailable"},
        {
            **complete_payload(),
            "evidence_grade": "local_rust_unit",
            "rollout_classification": "private_endpoint_only",
        },
        {
            **complete_payload(),
            "evidence_grade": "source_derived",
            "rollout_classification": "private_endpoint_only",
        },
    ],
)
def test_checked_schema_rejects_every_invalid_semantic_boundary(payload: Payload) -> None:
    assert_parity(payload, expected=False)


@pytest.mark.parametrize(
    "rollout_classification",
    ["ordinary_immediate_endpoint", "private_endpoint_only", "incompatible"],
)
def test_unavailable_schema_requires_inconclusive_rollout(
    rollout_classification: str,
) -> None:
    assert_parity(
        {**unavailable_payload(), "rollout_classification": rollout_classification},
        expected=False,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("format_version", "1"),
        ("client_release", 123),
        ("checks", [{"code": "client_behavior", "status": True}]),
    ],
)
def test_checked_schema_matches_pydantic_strict_types(field: str, value: JsonValue) -> None:
    assert_parity({**complete_payload(), field: value}, expected=False)


def test_format_version_boolean_is_rejected_at_python_and_json_boundaries() -> None:
    python_payload = {**complete_python_payload(), "format_version": True}
    json_payload = {**complete_payload(), "format_version": True}

    with pytest.raises(ValidationError):
        _ = LegacyClientResult.model_validate(python_payload)
    assert not accepts_with_pydantic(json_payload)
    assert not accepts_with_schema(json_payload)


def test_format_version_integer_one_remains_valid_at_python_and_json_boundaries() -> None:
    python_payload = complete_python_payload()
    json_payload = complete_payload()

    assert LegacyClientResult.model_validate(python_payload).format_version == 1
    assert_parity(json_payload, expected=True)


@pytest.mark.parametrize("field", ["unknown", *PROHIBITED_FIELDS])
def test_checked_schema_rejects_unknown_and_prohibited_concepts(field: str) -> None:
    assert_parity({**complete_payload(), field: "rejected"}, expected=False)


def test_checked_schema_rejects_unknown_nested_check_fields() -> None:
    payload = complete_payload()
    payload["checks"] = [
        {"code": "client_behavior", "status": "pass", "diagnostic": "rejected"}
    ]

    assert_parity(payload, expected=False)


def test_checked_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_model_schema_generation_is_stable_and_matches_checked_schema() -> None:
    first = LegacyClientResult.model_json_schema()
    second = LegacyClientResult.model_json_schema()

    assert first == second == SCHEMA
