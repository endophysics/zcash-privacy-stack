"""Immutable component status model and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

ABSENT: Final = "absent"
UNKNOWN: Final = "unknown"
UNCONFIGURED: Final = "unconfigured"


@unique
class Requirement(StrEnum):
    """Whether a component must be healthy for a successful status check."""

    REQUIRED = "required"
    OPTIONAL = "optional"


@unique
class ComponentState(StrEnum):
    """The observed checkout state for a component."""

    HEALTHY = "healthy"
    ABSENT = "absent"
    INVALID_REPOSITORY = "invalid_repository"
    REVISION_MISMATCH = "revision_mismatch"
    DIRTY = "dirty"
    UPSTREAM_ABSENT = "upstream_absent"
    UPSTREAM_MISMATCH = "upstream_mismatch"
    ORIGIN_ABSENT = "origin_absent"
    ORIGIN_MISMATCH = "origin_mismatch"
    ATTACHED_HEAD = "attached_head"
    UNCONFIGURED = "unconfigured"
    UNKNOWN = "unknown"


@unique
class DirtyState(StrEnum):
    """The working-tree state returned by Git."""

    CLEAN = "clean"
    DIRTY = "dirty"
    UNKNOWN = "unknown"


@unique
class HeadState(StrEnum):
    """The checkout attachment state returned by Git."""

    DETACHED = "detached"
    ATTACHED = "attached"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ComponentStatus:
    """Machine-readable status for one configured or optional component."""

    name: str
    requirement: Requirement
    state: ComponentState
    path: Path
    expected_revision: str
    current_revision: str
    expected_origin: str
    actual_origin: str
    head: HeadState
    dirty: DirtyState
    expected_upstream: str
    actual_upstream: str

    @property
    def is_acceptable(self) -> bool:
        """Return whether this status permits a successful process exit."""
        match self.requirement:
            case Requirement.REQUIRED:
                return self.state is ComponentState.HEALTHY
            case Requirement.OPTIONAL:
                return self.state in {
                    ComponentState.ABSENT,
                    ComponentState.HEALTHY,
                    ComponentState.UNCONFIGURED,
                }


@dataclass(frozen=True, slots=True)
class StatusReport:
    """The complete ordered status result for a component lock manifest."""

    components: tuple[ComponentStatus, ...]

    @property
    def exit_code(self) -> int:
        """Return zero only when every required component is healthy."""
        return 0 if all(component.is_acceptable for component in self.components) else 1


def render_status(report: StatusReport) -> str:
    """Render component statuses as ordered, space-separated key=value lines."""
    return "\n".join(_render_component(component) for component in report.components)


def _render_component(component: ComponentStatus) -> str:
    return (
        f"name={component.name} requirement={component.requirement.value} "
        f"state={component.state.value} path={component.path} "
        f"expected_revision={component.expected_revision} "
        f"current_revision={component.current_revision} "
        f"expected_origin={component.expected_origin} actual_origin={component.actual_origin} "
        f"head={component.head.value} "
        f"dirty={component.dirty.value} expected_upstream={component.expected_upstream} "
        f"actual_upstream={component.actual_upstream}"
    )
