from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which
from typing import Final

import pytest
from scripts import inspect_legacy_client
from scripts.wp06_legacy_client_contract import Client, LegacyClientResult

PROJECT_ROOT: Final = Path(__file__).parents[1]
SCENARIO_COUNT: Final = 10


def _run_just(arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    just = which("just")
    assert just is not None
    return subprocess.run(  # noqa: S603
        (just, "inspect-legacy-client", *arguments),
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("client", tuple(Client))
@pytest.mark.parametrize("format_value", ["human", "jsonl"])
def test_documented_just_invocations_render_ten_records_without_recipe_echo(
    client: Client, format_value: str
) -> None:
    arguments = (f"CLIENT={client.value}",) if format_value == "human" else (
        f"CLIENT={client.value}",
        "FORMAT=jsonl",
    )

    completed = _run_just(arguments)

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "uv run" not in completed.stdout
    if format_value == "human":
        assert completed.stdout.startswith(f"client={client.value}\n")
        assert completed.stdout.count("scenario=") == SCENARIO_COUNT
    else:
        records = tuple(
            LegacyClientResult.model_validate_json(line) for line in completed.stdout.splitlines()
        )
        assert len(records) == SCENARIO_COUNT
        assert all(record.client is client for record in records)


@pytest.mark.parametrize("client", [Client.ZODL_ANDROID, Client.ZODL_IOS])
def test_raw_positional_just_client_values_are_supported(client: Client) -> None:
    completed = _run_just((client.value,))

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.startswith(f"client={client.value}\n")
    assert completed.stdout.count("scenario=") == SCENARIO_COUNT


@pytest.mark.parametrize(
    ("client_value", "format_value", "client", "output_format"),
    [
        ("zodl-android", "jsonl", Client.ZODL_ANDROID, inspect_legacy_client.OutputFormat.JSONL),
        (
            "CLIENT=zodl-ios",
            "FORMAT=human",
            Client.ZODL_IOS,
            inspect_legacy_client.OutputFormat.HUMAN,
        ),
    ],
)
def test_parser_accepts_raw_and_exact_prefixed_values(
    client_value: str,
    format_value: str,
    client: Client,
    output_format: inspect_legacy_client.OutputFormat,
) -> None:
    request = inspect_legacy_client.parse_request(
        ("--client", client_value, "--format", format_value)
    )

    assert request.client is client
    assert request.output_format is output_format


def test_just_recipe_keeps_shell_metacharacters_as_invalid_cli_arguments(tmp_path: Path) -> None:
    marker = tmp_path / "command-substitution-ran"
    malicious_client = f"CLIENT=vizor$(touch {marker})"

    completed = _run_just((malicious_client,))

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.splitlines()[0] == "error: invalid_arguments"
    assert not marker.exists()


def test_just_recipe_keeps_prefixed_format_command_substitution_inert(tmp_path: Path) -> None:
    marker = tmp_path / "format-command-substitution-ran"
    malicious_format = f"FORMAT=jsonl$(touch {marker})"

    completed = _run_just(("CLIENT=zodl-android", malicious_format))

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.splitlines()[0] == "error: invalid_arguments"
    assert not marker.exists()
