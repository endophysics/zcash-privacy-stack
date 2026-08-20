"""WP06 legacy-client inspection CLI."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import Path
from typing import Final, TextIO, TypeAlias

from typing_extensions import override

from scripts.wp06_legacy_client_adapter_runtime import AdapterError, default_runtime
from scripts.wp06_legacy_client_adapters import (
    build_vizor_results,
    build_zodl_android_results,
    build_zodl_ios_results,
)
from scripts.wp06_legacy_client_contract import (
    Client,
    Execution,
    LegacyClientResult,
    TimelineEventCode,
    render_result,
)

ResultBuilder: TypeAlias = Callable[[Client, Path], tuple[LegacyClientResult, ...]]
SCRIPT_PATH: Final = Path(__file__)


@unique
class OutputFormat(StrEnum):
    """Available rendered result formats."""

    HUMAN = "human"
    JSONL = "jsonl"


@unique
class HumanTimelineStatus(StrEnum):
    """Fixed statuses for human timeline lines."""

    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"
    NOT_RUN = "not_run"


@unique
class CliErrorCode(StrEnum):
    """Stable command parsing failures."""

    INVALID_ARGUMENTS = "invalid_arguments"


@dataclass(frozen=True, slots=True)
class CliError(Exception):
    """Malformed command-line invocation."""

    code: CliErrorCode

    @override
    def __str__(self) -> str:
        return self.code.value


@dataclass(frozen=True, slots=True)
class InspectionRequest:
    """Validated client inspection inputs."""

    client: Client
    output_format: OutputFormat
    vizor_checkout: Path | None


@dataclass(frozen=True, slots=True)
class Console:
    """CLI output streams."""

    stdout: TextIO
    stderr: TextIO


def default_vizor_checkout(script_path: Path) -> Path:
    """Find Vizor beside the integration repository without using cwd."""
    return script_path.resolve().parents[3] / "vizor-wallet"


def parse_request(arguments: Sequence[str]) -> InspectionRequest:
    """Parse only the supported inspection arguments."""
    iterator = iter(arguments)
    client: Client | None = None
    output_format = OutputFormat.HUMAN
    checkout: Path | None = None
    for option in iterator:
        match option:
            case "--client":
                client = _parse_client(_next_argument(iterator).removeprefix("CLIENT="))
            case "--format":
                output_format = _parse_format(_next_argument(iterator).removeprefix("FORMAT="))
            case "--vizor-checkout":
                checkout = Path(_next_argument(iterator))
            case _:
                raise CliError(CliErrorCode.INVALID_ARGUMENTS)
    match client:
        case Client():
            return InspectionRequest(client, output_format, checkout)
        case None:
            raise CliError(CliErrorCode.INVALID_ARGUMENTS)


def _next_argument(arguments: Iterator[str]) -> str:
    try:
        return next(arguments)
    except StopIteration as error:
        raise CliError(CliErrorCode.INVALID_ARGUMENTS) from error


def _parse_client(value: str) -> Client:
    match value:
        case "vizor":
            return Client.VIZOR
        case "zodl-android":
            return Client.ZODL_ANDROID
        case "zodl-ios":
            return Client.ZODL_IOS
        case _:
            raise CliError(CliErrorCode.INVALID_ARGUMENTS)


def _parse_format(value: str) -> OutputFormat:
    match value:
        case "human":
            return OutputFormat.HUMAN
        case "jsonl":
            return OutputFormat.JSONL
        case _:
            raise CliError(CliErrorCode.INVALID_ARGUMENTS)


def build_results(client: Client, checkout: Path) -> tuple[LegacyClientResult, ...]:
    """Build the selected client's ordered evidence results."""
    match client:
        case Client.VIZOR:
            return build_vizor_results(checkout, default_runtime())
        case Client.ZODL_ANDROID:
            return build_zodl_android_results()
        case Client.ZODL_IOS:
            return build_zodl_ios_results()


def run_inspection(request: InspectionRequest, console: Console, builder: ResultBuilder) -> int:
    """Build every result before writing either supported output format."""
    checkout = request.vizor_checkout or default_vizor_checkout(SCRIPT_PATH)
    try:
        results = builder(request.client, checkout)
    except AdapterError as error:
        _ = console.stderr.write(f"error: {error.code.value}\n")
        return 1
    match request.output_format:
        case OutputFormat.HUMAN:
            _ = console.stdout.write(render_human(results))
        case OutputFormat.JSONL:
            _ = console.stdout.write(render_jsonl(results))
    return 0


def summarize_evidence(results: tuple[LegacyClientResult, ...]) -> str:
    """Count evidence grades in first-occurrence order."""
    grades = tuple(result.evidence_grade for result in results)
    first_seen = tuple(grade for index, grade in enumerate(grades) if grade not in grades[:index])
    return ",".join(f"{grade.value}:{grades.count(grade)}" for grade in first_seen)


def render_human(results: tuple[LegacyClientResult, ...]) -> str:
    """Render the result matrix with one truthful status for every timeline stage."""
    first = results[0]
    lines = [
        f"client={first.client.value}",
        f"release={first.client_release}",
        f"evidence_summary={summarize_evidence(results)}",
    ]
    for result in results:
        lines.extend(
            (
                f"scenario={result.scenario.value}",
                f"execution={result.execution.value}",
                f"evidence_grade={result.evidence_grade.value}",
                f"rollout_classification={result.rollout_classification.value}",
            )
        )
        for check in result.checks:
            status = check.status.value.upper()
            lines.append(f"check={check.code.value} status={status}")
        match result.execution:
            case Execution.UNAVAILABLE:
                match result.unavailable_reason:
                    case None:
                        raise AssertionError
                    case reason:
                        lines.append(f"unavailable_reason={reason.value}")
            case Execution.COMPLETE:
                pass
        lines.extend(_human_timeline(result))
    return "\n".join(lines) + "\n"


def _human_timeline(result: LegacyClientResult) -> tuple[str, ...]:
    observed_codes = frozenset(event.code for event in result.timeline)
    match result.execution:
        case Execution.UNAVAILABLE:
            statuses = tuple(HumanTimelineStatus.NOT_RUN for _ in TimelineEventCode)
        case Execution.COMPLETE:
            statuses = tuple(
                HumanTimelineStatus.OBSERVED
                if code in observed_codes
                else HumanTimelineStatus.NOT_OBSERVED
                for code in TimelineEventCode
            )
    return tuple(
        f"timeline={code.value} status={status.value}"
        for code, status in zip(TimelineEventCode, statuses, strict=True)
    )


def render_jsonl(results: tuple[LegacyClientResult, ...]) -> str:
    """Render individually contract-validated JSON Lines records."""
    lines = tuple(render_result(result) for result in results)
    for line in lines:
        _ = LegacyClientResult.model_validate_json(line)
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the direct command-line interface."""
    try:
        request = parse_request(sys.argv[1:] if argv is None else argv)
    except CliError as error:
        _ = sys.stderr.write(f"error: {error.code.value}\n")
        return 1
    return run_inspection(request, Console(sys.stdout, sys.stderr), build_results)


if __name__ == "__main__":
    raise SystemExit(main())
