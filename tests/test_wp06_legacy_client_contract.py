from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pytest
from jsonschema import Draft202012Validator
from pydantic import JsonValue, ValidationError
from scripts.wp06_legacy_client_contract import (
    SCENARIO_REGISTRY,
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
    UnavailableReason,
    render_result,
)

from tests.privacy_json import load_json_document

PROJECT_ROOT: Final = Path(__file__).parents[1]
SCHEMA_PATH: Final = PROJECT_ROOT / "interfaces" / "wp06-legacy-client-result.schema.json"


def valid_result() -> LegacyClientResult:
    return LegacyClientResult(
        client=Client.VIZOR,
        client_release="1.2.3",
        scenario=Scenario.EXACT_RETRY,
        evidence_grade=EvidenceGrade.LOCAL_RUST_UNIT,
        execution=Execution.COMPLETE,
        rollout_classification=RolloutClassification.ORDINARY_IMMEDIATE_ENDPOINT,
        checks=(CheckRecord(code=CheckCode.CLIENT_BEHAVIOR, status=CheckStatus.PASS),),
        timeline=(TimelineRecord(code=TimelineEventCode.SUBMISSION_CALL),),
    )


def unavailable_payload() -> dict[str, JsonValue]:
    payload = valid_result().model_dump(mode="json")
    payload.update(
        {
            "evidence_grade": EvidenceGrade.LOCAL_FLUTTER_UNAVAILABLE.value,
            "execution": Execution.UNAVAILABLE.value,
            "rollout_classification": RolloutClassification.INCONCLUSIVE.value,
            "checks": [{"code": CheckCode.CLIENT_BEHAVIOR.value, "status": "not_run"}],
            "timeline": [],
            "unavailable_reason": UnavailableReason.FLUTTER_TOOLCHAIN_UNAVAILABLE.value,
        }
    )
    return payload


def validate_payload(payload: dict[str, JsonValue]) -> LegacyClientResult:
    return LegacyClientResult.model_validate_json(json.dumps(payload))


def test_result_is_immutable_and_rejects_unknown_fields() -> None:
    result = valid_result()
    payload = result.model_dump(mode="json")
    payload["unknown"] = "rejected"

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)
    payload = valid_result().model_dump(mode="json")
    payload["checks"] = [
        {"code": CheckCode.CLIENT_BEHAVIOR.value, "status": "pass", "unknown": "rejected"}
    ]
    with pytest.raises(ValidationError):
        _ = validate_payload(payload)
    field_name = "client_release"
    with pytest.raises(ValidationError):
        setattr(result, field_name, "2.0.0")


def test_result_uses_strict_field_types_and_rejects_empty_release() -> None:
    payload = valid_result().model_dump(mode="json")
    payload["format_version"] = "1"

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)

    payload = valid_result().model_dump(mode="json")
    payload["client_release"] = ""

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_unavailable_execution_requires_reason() -> None:
    payload = unavailable_payload()
    _ = payload.pop("unavailable_reason")

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_unavailable_execution_requires_all_checks_not_run() -> None:
    payload = unavailable_payload()
    payload["checks"] = [{"code": CheckCode.CLIENT_BEHAVIOR.value, "status": "pass"}]

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_unavailable_execution_forbids_timeline() -> None:
    payload = unavailable_payload()
    payload["timeline"] = [{"code": TimelineEventCode.SUBMISSION_CALL.value}]

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_unavailable_execution_requires_inconclusive_rollout() -> None:
    payload = unavailable_payload()
    payload["rollout_classification"] = RolloutClassification.INCOMPATIBLE.value

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_complete_execution_forbids_unavailable_reason() -> None:
    payload = valid_result().model_dump(mode="json")
    payload["unavailable_reason"] = "not_applicable"

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_unavailable_reason_rejects_arbitrary_diagnostic_strings() -> None:
    payload = unavailable_payload()
    payload["unavailable_reason"] = "/private/checkout diagnostic"

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_unavailable_reason_renders_and_round_trips_as_enum() -> None:
    result = validate_payload(unavailable_payload())

    assert result.unavailable_reason is UnavailableReason.FLUTTER_TOOLCHAIN_UNAVAILABLE
    assert LegacyClientResult.model_validate_json(render_result(result)) == result


@pytest.mark.parametrize(
    "evidence_grade",
    [EvidenceGrade.LOCAL_RUST_UNIT, EvidenceGrade.SOURCE_DERIVED],
)
def test_source_and_local_unit_evidence_cannot_authorize_private_endpoint_only(
    evidence_grade: EvidenceGrade,
) -> None:
    payload = valid_result().model_dump(mode="json")
    payload["evidence_grade"] = evidence_grade.value
    payload["rollout_classification"] = RolloutClassification.PRIVATE_ENDPOINT_ONLY.value

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


@pytest.mark.parametrize(
    "evidence_grade",
    [EvidenceGrade.LOCAL_FLUTTER_UNAVAILABLE, EvidenceGrade.UNAVAILABLE],
)
def test_unavailable_evidence_requires_unavailable_execution(evidence_grade: EvidenceGrade) -> None:
    payload = valid_result().model_dump(mode="json")
    payload["evidence_grade"] = evidence_grade.value

    with pytest.raises(ValidationError):
        _ = validate_payload(payload)


def test_scenario_registry_and_timeline_codes_are_exact_and_ordered() -> None:
    assert tuple(SCENARIO_REGISTRY) == tuple(Scenario)
    assert [scenario.value for scenario in SCENARIO_REGISTRY] == [
        "temporary_public_absence",
        "exact_retry",
        "lost_response_retry",
        "transaction_status_reconciliation",
        "mempool_observation",
        "server_switching",
        "direct_fallback",
        "node_restart",
        "pre_release_conflict",
        "release_deadline_preservation",
    ]
    assert [event.value for event in TimelineEventCode] == [
        "submission_call",
        "server_acceptance",
        "client_visible_response",
        "client_retries_or_status_queries",
        "public_release",
        "client_final_state",
        "fallback_or_endpoint_change",
    ]


def test_renderer_is_sorted_deterministic_and_round_trips() -> None:
    result = valid_result()

    rendered = render_result(result)

    assert rendered == json.dumps(
        result.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    assert not rendered.endswith("\n")
    assert LegacyClientResult.model_validate_json(rendered) == result


def test_checked_in_schema_is_draft_2020_12_and_matches_model() -> None:
    schema = load_json_document(SCHEMA_PATH)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:zcash:privacy-stack:wp06-legacy-client-result:1"
    Draft202012Validator.check_schema(schema)
    assert schema == LegacyClientResult.model_json_schema()


def test_schema_excludes_prohibited_identifier_and_transport_concepts() -> None:
    schema_text = json.dumps(LegacyClientResult.model_json_schema(), sort_keys=True)

    for prohibited_field in (
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
    ):
        assert prohibited_field not in schema_text
