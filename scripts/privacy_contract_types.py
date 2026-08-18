"""Typed result models for privacy contract validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from pathlib import Path


JsonLocation: TypeAlias = tuple[str | int, ...]
MachineData: TypeAlias = tuple[tuple[str, str], ...]


@unique
class ContractKind(StrEnum):
    """Stable identifiers for independently versioned privacy contracts."""

    PRIVACY_POLICY = "urn:zcash:privacy-stack:privacy-policy:1"
    PRIVACY_CAPABILITIES = "urn:zcash:privacy-stack:privacy-capabilities:1"
    CANONICAL_READ_MANIFEST = "urn:zcash:privacy-stack:canonical-read-manifest:1"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One machine-readable reason a contract document is not valid."""

    code: str
    location: JsonLocation
    data: MachineData


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """The complete immutable outcome of validating one contract document."""

    kind: ContractKind
    source: Path
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether no validation issues were reported."""
        return not self.issues
