from __future__ import annotations

import os
from io import StringIO
from typing import TYPE_CHECKING

import pytest
from scripts import inspect_zakura

from tests.inspect_zakura_support import (
    Invocation,
    RecordingRunner,
    create_inspection_fixture,
    execute,
    supported_runtime,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_identity_preamble_reports_pinned_release_identity(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)

    exit_code, stdout, stderr = execute(fixture, supported_runtime(RecordingRunner()))

    assert exit_code == 0
    assert stderr == ""
    assert stdout.splitlines()[:5] == [
        "inspection=zakura_private_release",
        f"node_commit={fixture.git.second_revision}",
        f"upstream_base={fixture.upstream_base}",
        "observer=managed_zcashd_p2p",
        "host=Linux/x86_64",
    ]


def test_supported_host_invokes_zakura_recipe_with_cwd_and_environment(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)
    runner = RecordingRunner()
    environment = {"PATH": "/usr/bin", "INSPECTION_MARKER": "preserved"}

    exit_code, stdout, _ = execute(fixture, supported_runtime(runner, environment))

    assert exit_code == 0
    assert stdout.endswith("execution=complete\n")
    assert runner.invocations == [
        Invocation(
            command=("/usr/bin/just", "inspect-private-release"),
            cwd=fixture.git.repository,
            environment=environment,
        )
    ]


def test_darwin_arm64_reports_unavailable_without_invocation(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)
    runner = RecordingRunner()
    runtime = inspect_zakura.Runtime(inspect_zakura.Host("Darwin", "arm64"), {}, runner, None)

    exit_code, stdout, stderr = execute(fixture, runtime)

    assert exit_code == 0
    assert stderr == ""
    assert runner.invocations == []
    expected_tail = """execution=unavailable
reason=managed_zcashd_unavailable_on_darwin_arm64
override=TEST_ZCASHD_PATH
"""
    assert stdout.endswith(expected_tail)


def test_valid_zcashd_override_enables_darwin_arm64_invocation(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)
    binary = tmp_path / "zcashd"
    _ = binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o700)
    runner = RecordingRunner()
    environment = {"TEST_ZCASHD_PATH": str(binary)}
    runtime = inspect_zakura.Runtime(
        inspect_zakura.Host("Darwin", "aarch64"),
        environment,
        runner,
        "/opt/bin/just",
    )

    exit_code, stdout, stderr = execute(fixture, runtime)

    assert exit_code == 0
    assert stderr == ""
    assert stdout.endswith("execution=complete\n")
    assert runner.invocations[0].environment == environment


@pytest.mark.parametrize("kind", ["missing", "not_executable"])
def test_invalid_zcashd_override_fails_concisely(tmp_path: Path, kind: str) -> None:
    fixture = create_inspection_fixture(tmp_path)
    binary = tmp_path / "zcashd"
    if kind == "not_executable":
        _ = binary.write_text("not executable\n", encoding="utf-8")
        binary.chmod(0o600)
    runtime = inspect_zakura.Runtime(
        inspect_zakura.Host("Darwin", "arm64"),
        {"TEST_ZCASHD_PATH": str(binary)},
        RecordingRunner(),
        "/usr/bin/just",
    )

    exit_code, _, stderr = execute(fixture, runtime)

    assert exit_code == 1
    assert stderr == f"TEST_ZCASHD_PATH is not an executable file: {binary}\n"
    assert "Traceback" not in stderr


def test_revision_mismatch_fails_before_invocation(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)
    _ = fixture.lock_path.write_text(
        fixture.lock_path.read_text(encoding="utf-8").replace(
            fixture.git.second_revision,
            "0" * 40,
        ),
        encoding="utf-8",
    )
    runner = RecordingRunner()

    exit_code, _, stderr = execute(fixture, supported_runtime(runner))

    assert exit_code == 1
    assert stderr == "zakura: checkout HEAD does not match pinned revision\n"
    assert runner.invocations == []


def test_dirty_checkout_fails_before_invocation(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)
    _ = (fixture.git.repository / "fixture.txt").write_text("dirty\n", encoding="utf-8")
    runner = RecordingRunner()

    exit_code, _, stderr = execute(fixture, supported_runtime(runner))

    assert exit_code == 1
    assert stderr == "zakura: worktree is dirty\n"
    assert runner.invocations == []


def test_missing_lock_fails_without_traceback(tmp_path: Path) -> None:
    runner = RecordingRunner()
    stdout = StringIO()
    stderr = StringIO()

    exit_code = inspect_zakura.run_inspection(
        tmp_path / "components.lock.toml",
        supported_runtime(runner),
        inspect_zakura.Console(stdout, stderr),
    )

    assert exit_code == 1
    assert "components.lock.toml" in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()
    assert runner.invocations == []


def test_invalid_lock_fails_without_traceback(tmp_path: Path) -> None:
    lock_path = tmp_path / "components.lock.toml"
    _ = lock_path.write_text("format_version = 2\n", encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = inspect_zakura.run_inspection(
        lock_path,
        supported_runtime(RecordingRunner()),
        inspect_zakura.Console(stdout, stderr),
    )

    assert exit_code == 1
    assert "format_version" in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()


def test_child_failure_status_is_propagated_without_completion(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)

    exit_code, stdout, stderr = execute(fixture, supported_runtime(RecordingRunner(1)))

    assert exit_code == 1
    assert stderr == ""
    assert "execution=complete" not in stdout


def test_override_validation_uses_executable_file_contract(tmp_path: Path) -> None:
    fixture = create_inspection_fixture(tmp_path)
    directory = tmp_path / "zcashd"
    directory.mkdir()
    runtime = inspect_zakura.Runtime(
        inspect_zakura.Host("Darwin", "arm64"),
        {"TEST_ZCASHD_PATH": os.fspath(directory)},
        RecordingRunner(),
        "/usr/bin/just",
    )

    exit_code, _, stderr = execute(fixture, runtime)

    assert exit_code == 1
    assert "not an executable file" in stderr
