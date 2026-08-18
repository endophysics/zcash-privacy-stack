"""Typed parsing for the component lock manifest."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from string import hexdigits
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from pathlib import Path


REVISION_LENGTH = 40


RawScalar: TypeAlias = str | int | float | bool
RawValue: TypeAlias = RawScalar | list["RawValue"] | dict[str, "RawValue"]
RawTable: TypeAlias = dict[str, RawValue]


@dataclass(frozen=True, slots=True)
class ConfiguredComponent:
    """A component pinned to a specific repository revision."""

    name: str
    required: bool
    repository: str
    upstream: str | None
    revision: str
    upstream_base: str | None
    path: Path


@dataclass(frozen=True, slots=True)
class OptionalComponent:
    """A sibling component whose checkout is optional and unpinned."""

    name: str
    path: Path


Component: TypeAlias = ConfiguredComponent | OptionalComponent


@dataclass(frozen=True, slots=True)
class ComponentLock:
    """The validated immutable component lock document."""

    format_version: int
    components: tuple[Component, ...]


class ComponentLockError(Exception):
    """A lock manifest that cannot be parsed into the component model."""

    source: Path
    detail: str

    def __init__(self, source: Path, detail: str) -> None:
        """Initialize an error with the manifest source and validation detail."""
        self.source = source
        self.detail = detail
        super().__init__(f"{source}: {detail}")


@dataclass(frozen=True, slots=True)
class _LockSource:
    path: Path
    integration_root: Path


def load_component_lock(lock_path: Path) -> ComponentLock:
    """Parse a lock manifest into immutable configured and optional components."""
    source = _LockSource(path=lock_path.resolve(), integration_root=lock_path.resolve().parent)
    document = _read_document(source)
    _validate_document_keys(document, source)
    components_table = _components_table(document, source)
    components = tuple(
        _parse_component(name, value, source) for name, value in components_table.items()
    )
    _validate_unique_paths(components, source)
    return ComponentLock(format_version=_format_version(document, source), components=components)


def _read_document(source: _LockSource) -> RawTable:
    try:
        with source.path.open("rb") as lock_file:
            document: RawTable = tomllib.load(lock_file)
    except tomllib.TOMLDecodeError as error:
        raise ComponentLockError(source.path, f"invalid TOML: {error}") from error
    except OSError as error:
        raise ComponentLockError(source.path, str(error)) from error
    return document


def _validate_document_keys(document: RawTable, source: _LockSource) -> None:
    if set(document) != {"format_version", "components"}:
        raise ComponentLockError(source.path, "document must contain format_version and components")


def _format_version(document: RawTable, source: _LockSource) -> int:
    match document["format_version"]:
        case bool():
            raise ComponentLockError(source.path, "format_version must be integer 1")
        case int() as format_version if format_version == 1:
            return format_version
        case _:
            raise ComponentLockError(source.path, "format_version must be integer 1")


def _components_table(document: RawTable, source: _LockSource) -> RawTable:
    match document["components"]:
        case dict() as components:
            return components
        case _:
            raise ComponentLockError(source.path, "components must be a table")


def _parse_component(name: str, value: RawValue, source: _LockSource) -> Component:
    if not name.strip():
        raise ComponentLockError(source.path, "component name must not be empty")
    match value:
        case dict() as table:
            return _parse_component_table(name, table, source)
        case _:
            raise ComponentLockError(source.path, f"component {name} must be a table")


def _parse_component_table(name: str, table: RawTable, source: _LockSource) -> Component:
    if set(table) == {"path", "required"}:
        return _optional_component(name, table, source)
    return _configured_component(name, table, source)


def _required(table: RawTable, name: str, source: _LockSource) -> bool:
    match _field(table, "required", source):
        case bool() as required:
            return required
        case _:
            raise ComponentLockError(source.path, f"component {name}.required must be boolean")


def _configured_component(name: str, table: RawTable, source: _LockSource) -> ConfiguredComponent:
    base_fields = {"repository", "revision", "path", "required"}
    paired_fields = {"upstream", "upstream_base"}
    keys = set(table)
    if not (keys == base_fields or keys == base_fields | paired_fields):
        raise ComponentLockError(source.path, f"configured component {name} has invalid fields")
    repository = _nonempty_string(_field(table, "repository", source), f"{name}.repository", source)
    required = _required(table, name, source)
    revision = _revision(_field(table, "revision", source), f"{name}.revision", source)
    path = _component_path(_field(table, "path", source), name, source)
    if keys == base_fields:
        return ConfiguredComponent(name, required, repository, None, revision, None, path)
    upstream = _nonempty_string(_field(table, "upstream", source), f"{name}.upstream", source)
    upstream_base = _revision(
        _field(table, "upstream_base", source),
        f"{name}.upstream_base",
        source,
    )
    return ConfiguredComponent(name, required, repository, upstream, revision, upstream_base, path)


def _optional_component(name: str, table: RawTable, source: _LockSource) -> OptionalComponent:
    if set(table) != {"path", "required"}:
        raise ComponentLockError(source.path, f"optional component {name} has invalid fields")
    if _required(table, name, source):
        raise ComponentLockError(source.path, f"unconfigured component {name} must be optional")
    return OptionalComponent(name, _component_path(_field(table, "path", source), name, source))


def _field(table: RawTable, field_name: str, source: _LockSource) -> RawValue:
    try:
        return table[field_name]
    except KeyError as error:
        raise ComponentLockError(source.path, f"missing field {field_name}") from error


def _nonempty_string(value: RawValue, field_path: str, source: _LockSource) -> str:
    match value:
        case str() as string if string.strip():
            return string
        case _:
            raise ComponentLockError(source.path, f"component {field_path} must be nonempty")


def _revision(value: RawValue, field_path: str, source: _LockSource) -> str:
    revision = _nonempty_string(value, field_path, source)
    revision_is_hex = all(character in hexdigits for character in revision)
    if len(revision) != REVISION_LENGTH or not revision_is_hex:
        raise ComponentLockError(
            source.path,
            f"component {field_path} must be {REVISION_LENGTH} hex characters",
        )
    return revision.lower()


def _component_path(value: RawValue, name: str, source: _LockSource) -> Path:
    raw_path = _nonempty_string(value, f"{name}.path", source)
    path = (source.integration_root / raw_path).resolve()
    if path.parent != source.integration_root.parent:
        raise ComponentLockError(source.path, f"component {name}.path must resolve to a sibling")
    return path


def _validate_unique_paths(components: tuple[Component, ...], source: _LockSource) -> None:
    paths = tuple(component.path for component in components)
    if len(paths) != len(set(paths)):
        raise ComponentLockError(source.path, "components must not use duplicate canonical paths")
