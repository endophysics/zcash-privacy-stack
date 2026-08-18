"""Git-backed inspection for the component status model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.component_git import GitQuery, is_git_repository, query_git
from scripts.component_lock import (
    Component,
    ComponentLock,
    ConfiguredComponent,
    OptionalComponent,
    load_component_lock,
)
from scripts.component_status_model import (
    ABSENT,
    UNCONFIGURED,
    UNKNOWN,
    ComponentState,
    ComponentStatus,
    DirtyState,
    HeadState,
    Requirement,
    StatusReport,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class _Probe:
    revision: str
    origin: str
    head: HeadState
    dirty: DirtyState
    upstream: str


def inspect_lock_file(lock_path: Path) -> StatusReport:
    """Load and inspect the component lock file."""
    return inspect_lock(load_component_lock(lock_path))


def inspect_lock(lock: ComponentLock) -> StatusReport:
    """Inspect every component in a validated lock."""
    return StatusReport(tuple(_component_status(component) for component in lock.components))


def _component_status(component: Component) -> ComponentStatus:
    match component:
        case ConfiguredComponent():
            return _configured(component)
        case OptionalComponent():
            return _optional(component)


def _configured(component: ConfiguredComponent) -> ComponentStatus:
    requirement = Requirement.REQUIRED if component.required else Requirement.OPTIONAL
    expected_upstream = component.upstream or UNCONFIGURED
    if not component.path.exists():
        return ComponentStatus(
            name=component.name,
            requirement=requirement,
            state=ComponentState.ABSENT,
            path=component.path,
            expected_revision=component.revision,
            current_revision=ABSENT,
            expected_origin=component.repository,
            actual_origin=ABSENT,
            head=HeadState.UNKNOWN,
            dirty=DirtyState.UNKNOWN,
            expected_upstream=expected_upstream,
            actual_upstream=ABSENT,
        )
    if not is_git_repository(component.path):
        return ComponentStatus(
            name=component.name,
            requirement=requirement,
            state=ComponentState.INVALID_REPOSITORY,
            path=component.path,
            expected_revision=component.revision,
            current_revision=UNKNOWN,
            expected_origin=component.repository,
            actual_origin=UNKNOWN,
            head=HeadState.UNKNOWN,
            dirty=DirtyState.UNKNOWN,
            expected_upstream=expected_upstream,
            actual_upstream=UNKNOWN,
        )
    probe = _probe(component.path)
    return ComponentStatus(
        name=component.name,
        requirement=requirement,
        state=_state(component, probe),
        path=component.path,
        expected_revision=component.revision,
        current_revision=probe.revision,
        expected_origin=component.repository,
        actual_origin=probe.origin,
        head=probe.head,
        dirty=probe.dirty,
        expected_upstream=expected_upstream,
        actual_upstream=probe.upstream,
    )


def _optional(component: OptionalComponent) -> ComponentStatus:
    if not component.path.exists():
        return ComponentStatus(
            name=component.name,
            requirement=Requirement.OPTIONAL,
            state=ComponentState.ABSENT,
            path=component.path,
            expected_revision=UNCONFIGURED,
            current_revision=ABSENT,
            expected_origin=UNCONFIGURED,
            actual_origin=ABSENT,
            head=HeadState.UNKNOWN,
            dirty=DirtyState.UNKNOWN,
            expected_upstream=UNCONFIGURED,
            actual_upstream=ABSENT,
        )
    probe = _probe(component.path) if is_git_repository(component.path) else None
    if probe is None:
        return ComponentStatus(
            name=component.name,
            requirement=Requirement.OPTIONAL,
            state=ComponentState.UNCONFIGURED,
            path=component.path,
            expected_revision=UNCONFIGURED,
            current_revision=UNKNOWN,
            expected_origin=UNCONFIGURED,
            actual_origin=UNKNOWN,
            head=HeadState.UNKNOWN,
            dirty=DirtyState.UNKNOWN,
            expected_upstream=UNCONFIGURED,
            actual_upstream=UNKNOWN,
        )
    return ComponentStatus(
        name=component.name,
        requirement=Requirement.OPTIONAL,
        state=ComponentState.UNCONFIGURED,
        path=component.path,
        expected_revision=UNCONFIGURED,
        current_revision=probe.revision,
        expected_origin=UNCONFIGURED,
        actual_origin=probe.origin,
        head=probe.head,
        dirty=probe.dirty,
        expected_upstream=UNCONFIGURED,
        actual_upstream=probe.upstream,
    )


def _probe(path: Path) -> _Probe:
    revision = query_git(path, ("rev-parse", "HEAD"))
    attached = query_git(path, ("symbolic-ref", "-q", "HEAD"))
    origin = query_git(path, ("remote", "get-url", "origin"))
    dirty = query_git(path, ("status", "--porcelain"))
    upstream = query_git(path, ("remote", "get-url", "upstream"))
    if attached.succeeded:
        head = HeadState.ATTACHED
    elif revision.succeeded:
        head = HeadState.DETACHED
    else:
        head = HeadState.UNKNOWN
    return _Probe(
        revision=_value(revision, UNKNOWN),
        origin=_value(origin, ABSENT),
        head=head,
        dirty=DirtyState.DIRTY if dirty.output else DirtyState.CLEAN,
        upstream=_value(upstream, ABSENT),
    )


def _state(component: ConfiguredComponent, probe: _Probe) -> ComponentState:
    checkout_state = _checkout_state(component, probe)
    if checkout_state is not ComponentState.HEALTHY:
        return checkout_state
    origin_state = _origin_state(component, probe)
    if origin_state is not ComponentState.HEALTHY:
        return origin_state
    if probe.head is HeadState.ATTACHED:
        return ComponentState.ATTACHED_HEAD
    return _upstream_state(component, probe)


def _checkout_state(component: ConfiguredComponent, probe: _Probe) -> ComponentState:
    if probe.revision == UNKNOWN:
        return ComponentState.UNKNOWN
    if probe.revision != component.revision:
        return ComponentState.REVISION_MISMATCH
    if probe.dirty is DirtyState.DIRTY:
        return ComponentState.DIRTY
    return ComponentState.HEALTHY


def _origin_state(component: ConfiguredComponent, probe: _Probe) -> ComponentState:
    if probe.origin == ABSENT:
        return ComponentState.ORIGIN_ABSENT
    if probe.origin != component.repository:
        return ComponentState.ORIGIN_MISMATCH
    return ComponentState.HEALTHY


def _upstream_state(component: ConfiguredComponent, probe: _Probe) -> ComponentState:
    match component.upstream:
        case None:
            return ComponentState.HEALTHY
        case str() as upstream:
            if probe.upstream == ABSENT:
                return ComponentState.UPSTREAM_ABSENT
            if probe.upstream == upstream:
                return ComponentState.HEALTHY
            return ComponentState.UPSTREAM_MISMATCH


def _value(query: GitQuery, fallback: str) -> str:
    return query.output if query.succeeded else fallback
