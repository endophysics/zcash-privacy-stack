"""Offline schema selection and structural issue normalization."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, Protocol, assert_never

from jsonschema import Draft202012Validator, FormatChecker, SchemaError

from scripts.privacy_contract_json import (
    JsonDocument,
    JsonFileFailure,
    JsonFileFailureKind,
    load_json_document,
)
from scripts.privacy_contract_types import ContractKind, JsonLocation, ValidationIssue

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from jsonschema.exceptions import ValidationError
    from pydantic import JsonValue


class _SchemaValidator(Protocol):
    def iter_errors(self, instance: JsonDocument) -> Iterator[ValidationError]: ...


INTERFACES_ROOT: Final = Path(__file__).resolve().parents[1] / "interfaces"
SCHEMA_PATHS: Final[Mapping[ContractKind, Path]] = MappingProxyType(
    {
        ContractKind.PRIVACY_POLICY: INTERFACES_ROOT / "privacy-policy.schema.json",
        ContractKind.PRIVACY_CAPABILITIES: INTERFACES_ROOT / "privacy-capabilities.schema.json",
        ContractKind.CANONICAL_READ_MANIFEST: INTERFACES_ROOT
        / "canonical-read-manifest.schema.json",
    }
)
FORMAT_NAMES: Final = ("date-time", "uri", "uri-reference")
FORMAT_CHECKER: Final = FormatChecker(formats=FORMAT_NAMES)
CONSTRAINT_ISSUES: Final[Mapping[str, tuple[str, str]]] = MappingProxyType(
    {
        "minItems": ("schema.min_items", "minimum"),
        "maxItems": ("schema.max_items", "maximum"),
        "minLength": ("schema.min_length", "minimum"),
        "maxLength": ("schema.max_length", "maximum"),
        "minimum": ("schema.minimum", "minimum"),
        "exclusiveMinimum": ("schema.exclusive_minimum", "minimum"),
        "maximum": ("schema.maximum", "maximum"),
        "exclusiveMaximum": ("schema.exclusive_maximum", "maximum"),
        "type": ("schema.type", "expected"),
        "const": ("schema.const", "expected"),
        "enum": ("schema.enum", "allowed"),
    }
)


def load_schema(kind: ContractKind) -> JsonDocument | ValidationIssue:
    """Load and check the one local schema selected by contract kind."""
    loaded = load_json_document(SCHEMA_PATHS[kind])
    match loaded:
        case JsonFileFailure(kind=failure_kind, reason=reason):
            return _schema_file_issue(failure_kind, reason)
        case dict() as schema:
            if _contains_reference(schema):
                return ValidationIssue("schema.reference", (), (("keyword", "$ref"),))
            try:
                Draft202012Validator.check_schema(schema)
            except SchemaError as error:
                return ValidationIssue("schema.invalid", tuple(error.absolute_schema_path), ())
            return schema
        case _:
            assert_never(loaded)


def structural_issues(
    schema: JsonDocument,
    document: JsonDocument,
) -> tuple[ValidationIssue, ...]:
    """Collect all normalized structural failures without resolving references."""
    validator = _schema_validator(schema)
    issues: set[ValidationIssue] = set()
    for error in validator.iter_errors(document):
        issues.update(_normalize_error(schema, document, error))
    return tuple(issues)


def _schema_validator(schema: JsonDocument) -> _SchemaValidator:
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


def _schema_file_issue(kind: JsonFileFailureKind, reason: str) -> ValidationIssue:
    match kind:
        case JsonFileFailureKind.READ:
            return ValidationIssue("schema.read", (), (("reason", reason),))
        case JsonFileFailureKind.INVALID:
            return ValidationIssue("schema.invalid", (), (("reason", reason),))
        case _:
            assert_never(kind)


def _contains_reference(value: JsonValue) -> bool:
    match value:
        case dict() as fields:
            return "$ref" in fields or any(_contains_reference(child) for child in fields.values())
        case list() as items:
            return any(_contains_reference(item) for item in items)
        case None | bool() | int() | float() | str():
            return False
        case _:
            assert_never(value)


def _normalize_error(
    schema: JsonDocument,
    document: JsonDocument,
    error: ValidationError,
) -> tuple[ValidationIssue, ...]:
    location = tuple(error.absolute_path)
    keyword = error.validator
    if not isinstance(keyword, str):
        return (ValidationIssue("schema.invalid", location, ()),)
    constraint = _constraint_text(_constraint(schema, tuple(error.absolute_schema_path)))
    if keyword == "required":
        return _required_issues(document, location, _required_field(error.message))
    if keyword == "pattern":
        normalized = (
            "semver"
            if constraint == r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
            else constraint
        )
        return (ValidationIssue("schema.pattern", location, (("pattern", normalized),)),)
    if keyword == "format":
        normalized = "rfc3339" if constraint == "date-time" else constraint
        return (ValidationIssue("schema.format", location, (("format", normalized),)),)
    return (_constraint_issue(keyword, constraint, location),)


def _required_field(message: str) -> str:
    _, _, remainder = message.partition("'")
    field, _, _ = remainder.partition("'")
    return field


def _required_issues(
    document: JsonDocument,
    location: JsonLocation,
    field: str,
) -> tuple[ValidationIssue, ...]:
    if location == ("private_write",) and field == "epoch_ms":
        return (ValidationIssue("policy.fixed_epoch.requires_epoch_ms", location, ()),)
    if location == () and field == "attestation_bundle_url":
        if not _field_is_true(document, "private_write", "attestation_required"):
            return ()
        return (
            ValidationIssue(
                "policy.attestation.requires_bundle_url",
                (),
                (("field", field),),
            ),
        )
    if location == () and field == "canonical_manifest_url":
        if not _field_is_true(document, "read_privacy", "canonical_objects"):
            return ()
        return (
            ValidationIssue(
                "policy.canonical_reads.requires_manifest_url",
                (),
                (("field", field),),
            ),
        )
    return (ValidationIssue("schema.required", (*location, field), (("field", field),)),)


def _field_is_true(document: JsonDocument, section: str, field: str) -> bool:
    fields = document.get(section)
    return isinstance(fields, dict) and fields.get(field) is True


def _constraint_issue(
    keyword: str,
    constraint: str,
    location: JsonLocation,
) -> ValidationIssue:
    issue_details = CONSTRAINT_ISSUES.get(keyword)
    if issue_details is not None:
        code, data_key = issue_details
        return ValidationIssue(code, location, ((data_key, constraint),))
    return ValidationIssue(
        f"schema.{_snake_case(keyword)}",
        location,
        (("constraint", constraint),),
    )


def _constraint(schema: JsonDocument, location: JsonLocation) -> JsonValue:
    current: JsonValue = schema
    for segment in location:
        if isinstance(current, dict):
            if not isinstance(segment, str):
                return "invalid_schema_path"
            current = current[segment]
            continue
        if isinstance(current, list):
            if not isinstance(segment, int):
                return "invalid_schema_path"
            current = current[segment]
            continue
        return "invalid_schema_path"
    return current


def _constraint_text(value: JsonValue) -> str:
    match value:
        case None:
            return "null"
        case bool() as boolean:
            return "true" if boolean else "false"
        case str() as text:
            return text
        case int() | float() as number:
            return str(number)
        case list() as items:
            return ",".join(_constraint_text(item) for item in items)
        case dict() as fields:
            return ",".join(f"{key}:{_constraint_text(fields[key])}" for key in sorted(fields))
        case _:
            assert_never(value)


def _snake_case(keyword: str) -> str:
    return "".join(
        f"_{character.lower()}" if character.isupper() else character for character in keyword
    )
