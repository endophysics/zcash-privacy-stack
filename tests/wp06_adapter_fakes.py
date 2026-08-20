from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.wp06_legacy_client_adapter_runtime import CommandOutput

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class FakeCheckoutState:
    revision: str
    origin: str
    status: str = ""
    revision_status: int = 0
    origin_status: int = 0
    worktree_status: int = 0
    cargo_status: int = 0
    cargo_statuses: tuple[int, ...] = ()
    cargo_discoveries: tuple[CommandOutput, ...] = ()


class RecordingRunner:
    def __init__(self, state: FakeCheckoutState) -> None:
        self.state: FakeCheckoutState = state
        self.output_calls: list[tuple[tuple[str, ...], Path]] = []
        self.cargo_discovery_calls: list[tuple[tuple[str, ...], Path]] = []
        self.status_calls: list[tuple[tuple[str, ...], Path]] = []
        self.cargo_calls: list[tuple[tuple[str, ...], Path]] = []

    def output(self, command: tuple[str, ...], cwd: Path) -> CommandOutput:
        self.output_calls.append((command, cwd))
        match command[1:]:
            case ("rev-parse", "HEAD"):
                return CommandOutput(self.state.revision_status, self.state.revision)
            case ("remote", "get-url", "origin"):
                return CommandOutput(self.state.origin_status, self.state.origin)
            case ("status", "--porcelain"):
                return CommandOutput(self.state.worktree_status, self.state.status)
            case ("test", *_) as cargo_command:
                discovery_index = len(self.cargo_discovery_calls)
                self.cargo_discovery_calls.append((command, cwd))
                self.cargo_calls.append((command, cwd))
                if self.state.cargo_discoveries:
                    return self.state.cargo_discoveries[discovery_index]
                test_name = cargo_command[cargo_command.index("--lib") + 1]
                return CommandOutput(0, f"{test_name}: test")
            case unexpected:
                raise AssertionError(unexpected)

    def status(self, command: tuple[str, ...], cwd: Path) -> int:
        self.status_calls.append((command, cwd))
        self.cargo_calls.append((command, cwd))
        if self.state.cargo_statuses:
            return self.state.cargo_statuses[len(self.status_calls) - 1]
        return self.state.cargo_status


@dataclass(frozen=True, slots=True)
class FixedToolProbe:
    cargo: str | None

    def find(self, name: str) -> str | None:
        assert name == "cargo"
        return self.cargo
