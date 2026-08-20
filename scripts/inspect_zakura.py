"""Typed delegation to Zakura's private-release inspection surface."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, NoReturn, Protocol

from typing_extensions import override

from scripts.component_git import query_git
from scripts.component_lock import (
    ComponentLockError,
    ConfiguredComponent,
    OptionalComponent,
    load_component_lock,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import TextIO

INSPECTION_NAME: Final = "zakura_private_release"
OBSERVER_NAME: Final = "managed_zcashd_p2p"
OVERRIDE_NAME: Final = "TEST_ZCASHD_PATH"
UNAVAILABLE_REASON: Final = "managed_zcashd_unavailable_on_darwin_arm64"
ZAKURA_COMPONENT_NAME: Final = "zakura"


@dataclass(frozen=True, slots=True)
class Host:
    """Host identity used for capability decisions and reporting."""

    system: str
    machine: str


class Runner(Protocol):
    """Streaming child-process execution contract."""

    def run(
        self,
        command: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
    ) -> int:
        """Run a command with inherited standard streams and return its status."""
        ...


@dataclass(frozen=True, slots=True)
class Runtime:
    """Injectable host and process dependencies for one inspection."""

    host: Host
    environment: Mapping[str, str]
    runner: Runner
    just_executable: str | None


@dataclass(frozen=True, slots=True)
class Console:
    """Output streams for machine-readable wrapper records and errors."""

    stdout: TextIO
    stderr: TextIO


@dataclass(frozen=True, slots=True)
class InspectionError(Exception):
    """A concise operator-facing inspection precondition failure."""

    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


class _SubprocessRunner:
    def run(
        self,
        command: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
    ) -> int:
        completed = subprocess.run(command, cwd=cwd, env=environment, check=False)
        return completed.returncode


def run_inspection(lock_path: Path, runtime: Runtime, console: Console) -> int:
    """Validate the pinned checkout and delegate to Zakura's acceptance recipe."""
    try:
        component = _load_zakura(lock_path)
        _print_preamble(component, runtime.host, console.stdout)
        _require_checkout(component)
        override = runtime.environment.get(OVERRIDE_NAME)
        if override:
            _require_executable_override(Path(override))
        elif _managed_zcashd_is_unavailable(runtime.host):
            print("execution=unavailable", file=console.stdout)
            print(f"reason={UNAVAILABLE_REASON}", file=console.stdout)
            print(f"override={OVERRIDE_NAME}", file=console.stdout)
            return 0
        just_executable = _require_just(runtime.just_executable)
        console.stdout.flush()
        exit_code = runtime.runner.run(
            (just_executable, "inspect-private-release"),
            component.path,
            runtime.environment,
        )
    except (ComponentLockError, InspectionError) as error:
        print(error, file=console.stderr)
        return 1
    if exit_code == 0:
        print("execution=complete", file=console.stdout)
    return exit_code


def _load_zakura(lock_path: Path) -> ConfiguredComponent:
    lock = load_component_lock(lock_path)
    component = next(
        (candidate for candidate in lock.components if candidate.name == ZAKURA_COMPONENT_NAME),
        None,
    )
    match component:
        case ConfiguredComponent(upstream_base=str()):
            return component
        case ConfiguredComponent():
            return _fail_inspection("zakura: upstream_base is not configured")
        case OptionalComponent():
            return _fail_inspection("zakura: component is not configured")
        case None:
            return _fail_inspection("zakura: component is missing from lock")


def _print_preamble(component: ConfiguredComponent, host: Host, output: TextIO) -> None:
    print(f"inspection={INSPECTION_NAME}", file=output)
    print(f"node_commit={component.revision}", file=output)
    print(f"upstream_base={component.upstream_base}", file=output)
    print(f"observer={OBSERVER_NAME}", file=output)
    print(f"host={host.system}/{host.machine}", file=output)


def _require_checkout(component: ConfiguredComponent) -> None:
    head = query_git(component.path, ("rev-parse", "HEAD"))
    if not head.succeeded:
        _fail_inspection("zakura: checkout is not a Git worktree")
    if head.output != component.revision:
        _fail_inspection("zakura: checkout HEAD does not match pinned revision")
    status = query_git(component.path, ("status", "--porcelain"))
    if not status.succeeded:
        _fail_inspection("zakura: unable to inspect worktree status")
    if status.output:
        _fail_inspection("zakura: worktree is dirty")


def _require_executable_override(path: Path) -> None:
    if not path.is_file() or not os.access(path, os.X_OK):
        _fail_inspection(f"{OVERRIDE_NAME} is not an executable file: {path}")


def _require_just(executable: str | None) -> str:
    if executable is None:
        _fail_inspection("just executable not found")
    return executable


def _fail_inspection(detail: str) -> NoReturn:
    raise InspectionError(detail)


def _managed_zcashd_is_unavailable(host: Host) -> bool:
    return host.system.casefold() == "darwin" and host.machine.casefold() in {
        "arm64",
        "aarch64",
    }


def main() -> int:
    """Run the inspection from the integration repository root."""
    environment = dict(os.environ)
    runtime = Runtime(
        host=Host(system=platform.system(), machine=platform.machine()),
        environment=environment,
        runner=_SubprocessRunner(),
        just_executable=shutil.which("just", path=environment.get("PATH")),
    )
    return run_inspection(
        Path.cwd() / "components.lock.toml",
        runtime,
        Console(sys.stdout, sys.stderr),
    )


if __name__ == "__main__":
    raise SystemExit(main())
