"""Conservative bootstrap of configured component checkouts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scripts.component_git import GitCommand, is_git_repository, query_git, run_git
from scripts.component_lock import (
    Component,
    ComponentLock,
    ConfiguredComponent,
    OptionalComponent,
    load_component_lock,
)

if TYPE_CHECKING:
    from pathlib import Path


class BootstrapError(Exception):
    """A configured checkout that cannot be safely bootstrapped."""

    component: str
    detail: str

    def __init__(self, component: str, detail: str) -> None:
        """Initialize a concise component-scoped bootstrap failure."""
        self.component = component
        self.detail = detail
        super().__init__(f"{component}: {detail}")


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """The non-prose bootstrap outcome for one lock component."""

    name: str
    action: str


def bootstrap_lock_file(lock_path: Path) -> tuple[BootstrapResult, ...]:
    """Load and conservatively bootstrap every component in a lock file."""
    return bootstrap_lock(load_component_lock(lock_path))


def bootstrap_lock(lock: ComponentLock) -> tuple[BootstrapResult, ...]:
    """Bootstrap configured components and explicitly skip unconfigured optionals."""
    return tuple(_bootstrap_component(component) for component in lock.components)


def render_bootstrap(results: tuple[BootstrapResult, ...]) -> str:
    """Render ordered bootstrap results as machine-readable key=value lines."""
    return "\n".join(f"name={result.name} action={result.action}" for result in results)


def _bootstrap_component(component: Component) -> BootstrapResult:
    match component:
        case ConfiguredComponent():
            return _bootstrap_configured(component)
        case OptionalComponent():
            return BootstrapResult(component.name, "skipped")


def _bootstrap_configured(component: ConfiguredComponent) -> BootstrapResult:
    if component.path.exists():
        return _bootstrap_existing(component, "updated")
    command = run_git(
        component.path.parent,
        ("clone", "--origin", "origin", component.repository, str(component.path)),
    )
    _require_command(component, command, "clone failed")
    return _bootstrap_existing(component, "cloned")


def _bootstrap_existing(component: ConfiguredComponent, changed_action: str) -> BootstrapResult:
    if not is_git_repository(component.path):
        raise BootstrapError(component.name, "path is not a Git worktree")
    dirty = query_git(component.path, ("status", "--porcelain"))
    if not dirty.succeeded or dirty.output:
        raise BootstrapError(component.name, "worktree is dirty")
    _verify_remotes(component)
    revision = query_git(component.path, ("rev-parse", "--verify", _commit_ref(component)))
    if not revision.succeeded:
        _require_command(
            component,
            run_git(component.path, ("fetch", "origin")),
            "fetch origin failed",
        )
    revision = query_git(component.path, ("rev-parse", "--verify", _commit_ref(component)))
    if not revision.succeeded:
        raise BootstrapError(component.name, "pinned revision does not resolve to a commit")
    head = query_git(component.path, ("rev-parse", "HEAD"))
    attached = query_git(component.path, ("symbolic-ref", "-q", "HEAD"))
    if head.output == component.revision and not attached.succeeded:
        return BootstrapResult(component.name, "current")
    _require_command(
        component,
        run_git(component.path, ("checkout", "--detach", component.revision)),
        "checkout failed",
    )
    return BootstrapResult(component.name, changed_action)


def _verify_remotes(component: ConfiguredComponent) -> None:
    origin = query_git(component.path, ("remote", "get-url", "origin"))
    if not origin.succeeded or origin.output != component.repository:
        raise BootstrapError(component.name, "origin URL does not match lock repository")
    match component.upstream:
        case None:
            return
        case str() as expected_upstream:
            upstream = query_git(component.path, ("remote", "get-url", "upstream"))
            if not upstream.succeeded:
                _require_command(
                    component,
                    run_git(component.path, ("remote", "add", "upstream", expected_upstream)),
                    "adding upstream failed",
                )
                return
            if upstream.output != expected_upstream:
                raise BootstrapError(component.name, "upstream URL conflicts with lock repository")


def _require_command(
    component: ConfiguredComponent,
    command: GitCommand,
    action: str,
) -> None:
    if not command.succeeded:
        raise BootstrapError(component.name, action)


def _commit_ref(component: ConfiguredComponent) -> str:
    return f"{component.revision}^{{commit}}"
