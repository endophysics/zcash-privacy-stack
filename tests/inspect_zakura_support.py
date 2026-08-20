from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING

from scripts import inspect_zakura

from tests.git_fixture import GitFixture, create_git_fixture

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Invocation:
    command: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str]


class RecordingRunner:
    def __init__(self, exit_code: int = 0) -> None:
        self.exit_code: int = exit_code
        self.invocations: list[Invocation] = []

    def run(
        self,
        command: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
    ) -> int:
        self.invocations.append(Invocation(command, cwd, environment))
        return self.exit_code


@dataclass(frozen=True, slots=True)
class InspectionFixture:
    git: GitFixture
    lock_path: Path
    upstream_base: str


def create_inspection_fixture(tmp_path: Path) -> InspectionFixture:
    git = create_git_fixture(tmp_path)
    integration_root = tmp_path / "integration"
    integration_root.mkdir()
    lock_path = integration_root / "components.lock.toml"
    _ = lock_path.write_text(
        f"""\
format_version = 1

[components.zakura]
repository = "https://example.test/zakura.git"
upstream = "https://example.test/upstream.git"
revision = "{git.second_revision}"
upstream_base = "{git.first_revision}"
path = "../component"
required = true
""",
        encoding="utf-8",
    )
    return InspectionFixture(git, lock_path, git.first_revision)


def execute(
    fixture: InspectionFixture,
    runtime: inspect_zakura.Runtime,
) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    exit_code = inspect_zakura.run_inspection(
        fixture.lock_path,
        runtime,
        inspect_zakura.Console(stdout, stderr),
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


def supported_runtime(
    runner: RecordingRunner,
    environment: Mapping[str, str] | None = None,
) -> inspect_zakura.Runtime:
    return inspect_zakura.Runtime(
        host=inspect_zakura.Host(system="Linux", machine="x86_64"),
        environment={} if environment is None else environment,
        runner=runner,
        just_executable="/usr/bin/just",
    )
