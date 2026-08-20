"""Typed schema and input rules for the WP06 result contract."""

from __future__ import annotations

from typing import Final, TypeAlias

from pydantic import BeforeValidator, JsonValue
from pydantic_core import PydanticCustomError

JsonSchema: TypeAlias = dict[str, JsonValue]
BOOLEAN_FORMAT_VERSION_ERROR: Final = "format_version_boolean_forbidden"
BOOLEAN_FORMAT_VERSION_MESSAGE: Final = "Format version must be an integer"


def _reject_boolean_format_version(value: JsonValue) -> JsonValue:
    if isinstance(value, bool):
        raise PydanticCustomError(BOOLEAN_FORMAT_VERSION_ERROR, BOOLEAN_FORMAT_VERSION_MESSAGE)
    return value


FORMAT_VERSION_BEFORE_VALIDATOR: Final[BeforeValidator] = BeforeValidator(
    _reject_boolean_format_version
)

UNAVAILABLE_EXECUTION_RULE: Final[JsonSchema] = {
    "if": {
        "properties": {"execution": {"const": "unavailable"}},
        "required": ["execution"],
    },
    "then": {
        "properties": {
            "checks": {
                "items": {
                    "properties": {"status": {"const": "not_run"}},
                    "required": ["status"],
                }
            },
            "rollout_classification": {"const": "inconclusive"},
            "timeline": {"maxItems": 0},
            "unavailable_reason": {"not": {"type": "null"}},
        },
        "required": ["unavailable_reason"],
    },
}

COMPLETE_EXECUTION_RULE: Final[JsonSchema] = {
    "if": {
        "properties": {"execution": {"const": "complete"}},
        "required": ["execution"],
    },
    "then": {"properties": {"unavailable_reason": {"type": "null"}}},
}

UNAVAILABLE_EVIDENCE_RULE: Final[JsonSchema] = {
    "if": {
        "properties": {
            "evidence_grade": {
                "enum": ["local_flutter_unavailable", "unavailable"],
            }
        },
        "required": ["evidence_grade"],
    },
    "then": {"properties": {"execution": {"const": "unavailable"}}},
}

PRIVATE_ENDPOINT_EVIDENCE_RULE: Final[JsonSchema] = {
    "if": {
        "properties": {
            "evidence_grade": {"enum": ["local_rust_unit", "source_derived"]},
        },
        "required": ["evidence_grade"],
    },
    "then": {
        "properties": {
            "rollout_classification": {"not": {"const": "private_endpoint_only"}},
        }
    },
}

LEGACY_CLIENT_RESULT_SCHEMA_RULES: Final[tuple[JsonSchema, ...]] = (
    UNAVAILABLE_EXECUTION_RULE,
    COMPLETE_EXECUTION_RULE,
    UNAVAILABLE_EVIDENCE_RULE,
    PRIVATE_ENDPOINT_EVIDENCE_RULE,
)
