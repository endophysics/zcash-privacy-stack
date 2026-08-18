"""Strict typed JSON file boundary for privacy contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import TYPE_CHECKING, Final, TypeAlias

from pydantic import JsonValue, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from pathlib import Path


JsonDocument: TypeAlias = dict[str, JsonValue]
JSON_DOCUMENT_ADAPTER: Final = TypeAdapter(JsonDocument)


@unique
class JsonFileFailureKind(StrEnum):
    """The expected ways a JSON object file can fail at its boundary."""

    READ = "read"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class JsonFileFailure:
    """A machine-readable JSON object loading failure."""

    kind: JsonFileFailureKind
    reason: str


def load_json_document(path: Path) -> JsonDocument | JsonFileFailure:
    """Read and parse a file as one recursively typed JSON object."""
    try:
        content = path.read_bytes()
    except OSError as error:
        return JsonFileFailure(JsonFileFailureKind.READ, type(error).__name__)
    try:
        return JSON_DOCUMENT_ADAPTER.validate_json(content)
    except ValidationError:
        return JsonFileFailure(JsonFileFailureKind.INVALID, "pydantic_validation")
