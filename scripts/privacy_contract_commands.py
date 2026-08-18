"""Offline command implementations for the WP01 privacy contracts."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from scripts.privacy_contract_types import ContractKind, MachineData, ValidationIssue
from scripts.privacy_contract_validation import (
    ValidationOutput,
    encode_json,
    render_validation_error,
    render_validation_report,
    validate_document,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class ValidateArguments:
    """Parsed inputs to the privacy-policy validation command."""

    path: Path
    check_freshness: bool
    at: datetime | None


@dataclass(frozen=True, slots=True)
class ArgumentFailure:
    """An expected machine-readable command argument failure."""

    code: str
    data: MachineData


@dataclass(frozen=True, slots=True)
class _ParseState:
    path: Path | None
    check_freshness: bool
    at: datetime | None


def run_policy_validate(arguments: Sequence[str]) -> int:
    """Parse, validate, and render one local privacy policy document."""
    parsed = parse_policy_validate(arguments)
    if isinstance(parsed, ArgumentFailure):
        issue = ValidationIssue(parsed.code, (), parsed.data)
        _write_json(
            render_validation_error(ContractKind.PRIVACY_POLICY.value, issue),
            sys.stderr,
        )
        return 1

    report = validate_document(
        ContractKind.PRIVACY_POLICY,
        parsed.path,
        check_freshness=parsed.check_freshness,
        at=parsed.at,
    )
    if report.is_valid:
        _write_json(render_validation_report(report), sys.stdout)
        return 0
    _write_json(render_validation_report(report), sys.stderr)
    return 1


def parse_policy_validate(arguments: Sequence[str]) -> ValidateArguments | ArgumentFailure:
    """Parse the intentionally small policy validation command grammar."""
    parsed = _parse_policy_arguments(
        tuple(arguments),
        _ParseState(path=None, check_freshness=False, at=None),
    )
    if isinstance(parsed, ArgumentFailure):
        return parsed
    if parsed.path is None:
        return ArgumentFailure("argument.path_required", ())
    if not parsed.check_freshness and parsed.at is not None:
        return ArgumentFailure("argument.at_requires_freshness", (("option", "--at"),))
    return ValidateArguments(
        path=parsed.path,
        check_freshness=parsed.check_freshness,
        at=parsed.at,
    )


def _parse_policy_arguments(
    arguments: tuple[str, ...], state: _ParseState
) -> _ParseState | ArgumentFailure:
    if not arguments:
        return state

    argument = arguments[0]
    remaining = arguments[1:]
    if argument == "--check-freshness":
        outcome = (
            ArgumentFailure("argument.duplicate_option", (("option", "--check-freshness"),))
            if state.check_freshness
            else _parse_policy_arguments(
                remaining,
                _ParseState(path=state.path, check_freshness=True, at=state.at),
            )
        )
    elif argument == "--at":
        if not remaining:
            outcome = ArgumentFailure("argument.missing_value", (("option", "--at"),))
        else:
            parsed_at = _parse_rfc3339_utc(remaining[0])
            if isinstance(parsed_at, ArgumentFailure):
                outcome = parsed_at
            elif state.at is not None:
                outcome = ArgumentFailure("argument.duplicate_option", (("option", "--at"),))
            else:
                outcome = _parse_policy_arguments(
                    remaining[1:],
                    _ParseState(
                        path=state.path,
                        check_freshness=state.check_freshness,
                        at=parsed_at,
                    ),
                )
    elif argument.startswith("--"):
        outcome = ArgumentFailure("argument.unknown_option", (("option", argument),))
    elif state.path is not None:
        outcome = ArgumentFailure("argument.unexpected_value", (("value", argument),))
    else:
        outcome = _parse_policy_arguments(
            remaining,
            _ParseState(
                path=Path(argument),
                check_freshness=state.check_freshness,
                at=state.at,
            ),
        )
    return outcome


def _parse_rfc3339_utc(value: str) -> datetime | ArgumentFailure:
    if not value.endswith("Z") or "T" not in value:
        return ArgumentFailure("argument.at_format", (("format", "rfc3339_utc"),))
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return ArgumentFailure("argument.at_format", (("format", "rfc3339_utc"),))


def _write_json(document: ValidationOutput, stream: TextIO) -> None:
    _ = stream.write(f"{encode_json(document)}\n")
