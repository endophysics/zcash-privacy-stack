from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Final

import pytest
from scripts import inspect_legacy_client
from scripts.wp06_legacy_client_adapter_runtime import (
    VIZOR_PIN,
    AdapterError,
    AdapterErrorCode,
    AdapterRuntime,
)
from scripts.wp06_legacy_client_adapters import (
    build_vizor_results,
    build_zodl_android_results,
    build_zodl_ios_results,
)
from scripts.wp06_legacy_client_contract import (
    SCENARIO_REGISTRY,
    Client,
    LegacyClientResult,
)

from tests.wp06_adapter_fakes import FakeCheckoutState, FixedToolProbe, RecordingRunner

PROJECT_ROOT: Final = Path(__file__).parents[1]
VALID_STATE: Final = FakeCheckoutState(revision=VIZOR_PIN.revision, origin=VIZOR_PIN.repository)


def _fixture_results(
    client: Client, checkout: Path
) -> tuple[LegacyClientResult, ...]:
    match client:
        case Client.VIZOR:
            checkout.mkdir(exist_ok=True)
            runtime = AdapterRuntime(
                RecordingRunner(VALID_STATE), FixedToolProbe("/toolchain/cargo")
            )
            return build_vizor_results(checkout, runtime)
        case Client.ZODL_ANDROID:
            return build_zodl_android_results()
        case Client.ZODL_IOS:
            return build_zodl_ios_results()


def inspect_fixture(
    client: Client, checkout: Path, output_format: inspect_legacy_client.OutputFormat
) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    request = inspect_legacy_client.InspectionRequest(client, output_format, checkout)
    exit_code = inspect_legacy_client.run_inspection(
        request,
        inspect_legacy_client.Console(stdout, stderr),
        _fixture_results,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize(
    ("client", "release", "important_line"),
    [
        (Client.VIZOR, "0.0.48", "timeline=submission_call status=observed"),
        (Client.ZODL_ANDROID, "3.9.3-2393", "check=direct_fallback status=FAIL"),
        (Client.ZODL_IOS, "3.9.5", "check=direct_fallback status=NOT_RUN"),
    ],
)
def test_human_inspection_renders_preamble_scenarios_and_honest_timelines(
    tmp_path: Path, client: Client, release: str, important_line: str
) -> None:
    exit_code, stdout, stderr = inspect_fixture(
        client, tmp_path / "vizor", inspect_legacy_client.OutputFormat.HUMAN
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout.splitlines()[:3] == [
        f"client={client.value}",
        f"release={release}",
        "evidence_summary="
        + inspect_legacy_client.summarize_evidence(_fixture_results(client, tmp_path / "summary")),
    ]
    scenario_lines = [
        line.removeprefix("scenario=")
        for line in stdout.splitlines()
        if line.startswith("scenario=")
    ]
    assert scenario_lines == [
        scenario.value for scenario in SCENARIO_REGISTRY
    ]
    assert important_line in stdout


@pytest.mark.parametrize("client", tuple(Client))
def test_jsonl_uses_contract_records_in_registry_order_and_is_deterministic(
    tmp_path: Path, client: Client
) -> None:
    first = inspect_fixture(client, tmp_path / "first", inspect_legacy_client.OutputFormat.JSONL)
    second = inspect_fixture(client, tmp_path / "second", inspect_legacy_client.OutputFormat.JSONL)

    assert first[0] == second[0] == 0
    assert first[2] == second[2] == ""
    assert first[1] == second[1]
    assert first[1].endswith("\n")
    assert not first[1].endswith("\n\n")
    records = tuple(LegacyClientResult.model_validate_json(line) for line in first[1].splitlines())
    assert tuple(record.scenario for record in records) == SCENARIO_REGISTRY
    assert [json.loads(line) for line in first[1].splitlines()] == [
        result.model_dump(mode="json") for result in _fixture_results(client, tmp_path / "expected")
    ]


def test_adapter_failure_is_stable_and_emits_no_partial_result(tmp_path: Path) -> None:
    def fail(_client: Client, _checkout: Path) -> tuple[LegacyClientResult, ...]:
        raise AdapterError(AdapterErrorCode.CARGO_EVIDENCE_FAILED)

    stdout = StringIO()
    stderr = StringIO()
    request = inspect_legacy_client.InspectionRequest(
        Client.VIZOR, inspect_legacy_client.OutputFormat.HUMAN, tmp_path / "vizor"
    )

    console = inspect_legacy_client.Console(stdout, stderr)
    exit_code = inspect_legacy_client.run_inspection(request, console, fail)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "error: cargo_evidence_failed\n"


@pytest.mark.parametrize(
    "arguments",
    [
        ("--client", "unknown"),
        ("--client", "vizor", "--format", "unknown"),
        ("--format", "jsonl"),
    ],
)
def test_invalid_client_or_format_is_rejected(arguments: tuple[str, ...]) -> None:
    with pytest.raises(inspect_legacy_client.CliError):
        _ = inspect_legacy_client.parse_request(arguments)


def test_default_vizor_checkout_uses_zcash_level_sibling_not_privup_level_sibling() -> None:
    checkout = inspect_legacy_client.default_vizor_checkout(
        PROJECT_ROOT / "scripts" / "inspect_legacy_client.py"
    )

    assert checkout == PROJECT_ROOT.parents[1] / "vizor-wallet"
    assert checkout != PROJECT_ROOT.parent / "vizor-wallet"


def test_default_vizor_checkout_uses_actual_module_script_path_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    checkout = inspect_legacy_client.default_vizor_checkout(inspect_legacy_client.SCRIPT_PATH)

    assert checkout == PROJECT_ROOT.parents[1] / "vizor-wallet"
    assert checkout != PROJECT_ROOT.parent / "vizor-wallet"


@pytest.mark.parametrize("client", tuple(Client))
def test_human_output_has_no_paths_identifiers_or_times(tmp_path: Path, client: Client) -> None:
    _, output, _ = inspect_fixture(
        client, tmp_path / client.value, inspect_legacy_client.OutputFormat.HUMAN
    )

    prohibited_values = (
        "/Users",
        "https://",
        VIZOR_PIN.revision,
        "timestamp",
        "duration",
        "transaction_id",
    )
    for prohibited in prohibited_values:
        assert prohibited not in output
