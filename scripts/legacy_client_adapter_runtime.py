"""Strict local runtime for the Vizor evidence adapter."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum, unique
from typing import TYPE_CHECKING, Final, Protocol

from typing_extensions import override

from scripts.vizor_evidence import (
    VIZOR_RUST_EVIDENCE_REGISTRY,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ClientPin:
    """Immutable release, revision, and repository identity."""

    release: str
    revision: str
    repository: str


VIZOR_PIN: Final = ClientPin(
    "0.0.48",
    "d60ea8ef853d02e6ea31573e75c5603db1d7addb",
    "https://github.com/chainapsis/vizor-wallet",
)
ZODL_ANDROID_PIN: Final = ClientPin(
    "3.9.3-2393",
    "39cf778399dc49e2fa24fe08b9b1cd83adf0fa7f",
    "https://github.com/zodl-inc/zodl-android",
)
ZODL_IOS_PIN: Final = ClientPin(
    "3.9.5",
    "993d31f333f6fe118819f5c8464008801c3f8908",
    "https://github.com/zodl-inc/zodl-ios",
)


@dataclass(frozen=True, slots=True)
class CommandOutput:
    """Captured output for a read-only preflight command."""

    return_code: int
    stdout: str


class CommandRunner(Protocol):
    """Non-shell command execution seam."""

    def output(self, command: tuple[str, ...], cwd: Path) -> CommandOutput:
        """Run a read-only command and capture its output."""
        ...

    def status(self, command: tuple[str, ...], cwd: Path) -> int:
        """Run an evidence command and return only its status."""
        ...


class ToolProbe(Protocol):
    """Executable lookup seam."""

    def find(self, name: str) -> str | None:
        """Resolve an executable name without invoking it."""
        ...


@dataclass(frozen=True, slots=True)
class AdapterRuntime:
    """Injected command and tool probes."""

    command_runner: CommandRunner
    tool_probe: ToolProbe


@unique
class AdapterErrorCode(StrEnum):
    """Stable adapter failure states."""

    VIZOR_CHECKOUT_UNAVAILABLE = "vizor_checkout_unavailable"
    VIZOR_REVISION_MISMATCH = "vizor_revision_mismatch"
    VIZOR_ORIGIN_MISMATCH = "vizor_origin_mismatch"
    VIZOR_WORKTREE_DIRTY = "vizor_worktree_dirty"
    CARGO_UNAVAILABLE = "cargo_unavailable"
    CARGO_EVIDENCE_MISSING = "cargo_evidence_missing"
    CARGO_EVIDENCE_FAILED = "cargo_evidence_failed"


@dataclass(frozen=True, slots=True)
class AdapterError(Exception):
    """Typed adapter failure that cannot emit false evidence."""

    code: AdapterErrorCode

    @override
    def __str__(self) -> str:
        return self.code.value


class SubprocessCommandRunner:
    """Run tuple commands directly without a shell."""

    def output(self, command: tuple[str, ...], cwd: Path) -> CommandOutput:
        """Capture output needed only for checkout preflight."""
        try:
            completed = subprocess.run(  # noqa: S603
                command,
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return CommandOutput(127, "")
        return CommandOutput(completed.returncode, completed.stdout.strip())

    def status(self, command: tuple[str, ...], cwd: Path) -> int:
        """Return only command status, discarding evidence-command output."""
        try:
            completed = subprocess.run(  # noqa: S603
                command,
                cwd=cwd,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return 127
        return completed.returncode


class SystemToolProbe:
    """Resolve executables from the inherited process path."""

    def find(self, name: str) -> str | None:
        """Return the resolved executable path when present."""
        return shutil.which(name)


def default_runtime() -> AdapterRuntime:
    """Build the real local adapter runtime."""
    return AdapterRuntime(command_runner=SubprocessCommandRunner(), tool_probe=SystemToolProbe())


def run_vizor_cargo_evidence(checkout: Path, runtime: AdapterRuntime) -> None:
    """Require the pinned checkout and run each exact Rust evidence test once."""
    cargo = _require_vizor_preflight(checkout, runtime)
    manifest = str(checkout / "rust" / "Cargo.toml")
    for evidence in VIZOR_RUST_EVIDENCE_REGISTRY:
        command = _cargo_evidence_command(cargo, manifest, evidence.test_name)
        listing = runtime.command_runner.output((*command, "--list"), checkout)
        expected_listing = f"{evidence.test_name}: test"
        if listing.return_code != 0 or expected_listing not in listing.stdout.splitlines():
            raise AdapterError(AdapterErrorCode.CARGO_EVIDENCE_MISSING)
        if runtime.command_runner.status(command, checkout) != 0:
            raise AdapterError(AdapterErrorCode.CARGO_EVIDENCE_FAILED)


def _cargo_evidence_command(cargo: str, manifest: str, test_name: str) -> tuple[str, ...]:
    return (
        cargo,
        "test",
        "--locked",
        "--offline",
        "--manifest-path",
        manifest,
        "--lib",
        test_name,
        "--",
        "--exact",
    )


def _require_vizor_preflight(checkout: Path, runtime: AdapterRuntime) -> str:
    if not checkout.is_dir():
        raise AdapterError(AdapterErrorCode.VIZOR_CHECKOUT_UNAVAILABLE)
    head = runtime.command_runner.output(("git", "rev-parse", "HEAD"), checkout)
    if head.return_code != 0:
        raise AdapterError(AdapterErrorCode.VIZOR_CHECKOUT_UNAVAILABLE)
    if head.stdout != VIZOR_PIN.revision:
        raise AdapterError(AdapterErrorCode.VIZOR_REVISION_MISMATCH)
    origin = runtime.command_runner.output(("git", "remote", "get-url", "origin"), checkout)
    if origin.return_code != 0 or origin.stdout != VIZOR_PIN.repository:
        raise AdapterError(AdapterErrorCode.VIZOR_ORIGIN_MISMATCH)
    status = runtime.command_runner.output(("git", "status", "--porcelain"), checkout)
    if status.return_code != 0 or status.stdout:
        raise AdapterError(AdapterErrorCode.VIZOR_WORKTREE_DIRTY)
    cargo = runtime.tool_probe.find("cargo")
    if cargo is None:
        raise AdapterError(AdapterErrorCode.CARGO_UNAVAILABLE)
    return cargo
