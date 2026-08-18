from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from scripts import component_lock

from tests.git_fixture import create_git_fixture

if TYPE_CHECKING:
    from pathlib import Path


REVISION_LENGTH = 40


def write_lock(tmp_path: Path, content: str) -> Path:
    lock_path = tmp_path / "integration" / "components.lock.toml"
    lock_path.parent.mkdir()
    _ = lock_path.write_text(content, encoding="utf-8")
    return lock_path


def test_load_component_lock_parses_configured_and_optional_components(tmp_path: Path) -> None:
    lock_path = write_lock(
        tmp_path,
        """\
format_version = 1

[components.zakura]
repository = "https://example.test/zakura.git"
upstream = "https://example.test/upstream.git"
revision = "0123456789abcdef0123456789abcdef01234567"
upstream_base = "76543210fedcba9876543210fedcba9876543210"
path = "../zakura"
required = true

[components.gateway]
path = "../gateway"
required = false
""",
    )

    lock = component_lock.load_component_lock(lock_path)

    assert lock.format_version == 1
    assert lock.components[0] == component_lock.ConfiguredComponent(
        name="zakura",
        repository="https://example.test/zakura.git",
        upstream="https://example.test/upstream.git",
        revision="0123456789abcdef0123456789abcdef01234567",
        upstream_base="76543210fedcba9876543210fedcba9876543210",
        path=(tmp_path / "zakura").resolve(),
        required=True,
    )
    assert lock.components[1] == component_lock.OptionalComponent(
        name="gateway",
        path=(tmp_path / "gateway").resolve(),
    )


def test_load_component_lock_parses_configured_optional_component(tmp_path: Path) -> None:
    lock_path = write_lock(
        tmp_path,
        """\
format_version = 1

[components.gateway]
repository = "https://example.test/gateway.git"
revision = "0123456789abcdef0123456789abcdef01234567"
path = "../gateway"
required = false
""",
    )

    lock = component_lock.load_component_lock(lock_path)

    assert lock.components == (
        component_lock.ConfiguredComponent(
            name="gateway",
            repository="https://example.test/gateway.git",
            upstream=None,
            revision="0123456789abcdef0123456789abcdef01234567",
            upstream_base=None,
            path=(tmp_path / "gateway").resolve(),
            required=False,
        ),
    )


def test_load_component_lock_normalizes_uppercase_revisions(tmp_path: Path) -> None:
    revision = "0123456789ABCDEF0123456789ABCDEF01234567"
    lock_path = write_lock(
        tmp_path,
        f"""\
format_version = 1
[components.zakura]
repository = "https://example.test/zakura.git"
upstream = "https://example.test/upstream.git"
revision = "{revision}"
upstream_base = "{revision}"
path = "../zakura"
required = true
""",
    )

    lock = component_lock.load_component_lock(lock_path)

    component = lock.components[0]
    assert isinstance(component, component_lock.ConfiguredComponent)
    assert component.revision == revision.lower()
    assert component.upstream_base == revision.lower()


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        ("format_version = 2\n[components]\n", "format_version"),
        ("format_version = 1\ncomponents = []\n", "components"),
        (
            "format_version = 1\n[components.gateway]\npath = 1\nrequired = false\n",
            "path",
        ),
        (
            'format_version = 1\n[components.gateway]\npath = "../gateway"\nrequired = "false"\n',
            "required",
        ),
    ],
)
def test_load_component_lock_rejects_invalid_document_shapes(
    tmp_path: Path,
    content: str,
    reason: str,
) -> None:
    lock_path = write_lock(tmp_path, content)

    with pytest.raises(component_lock.ComponentLockError, match=reason):
        _ = component_lock.load_component_lock(lock_path)


@pytest.mark.parametrize(
    "content",
    [
        """\
format_version = 1
[components.zakura]
repository = ""
revision = "0123456789abcdef0123456789abcdef01234567"
path = "../zakura"
required = true
""",
        """\
format_version = 1
[components.zakura]
repository = "https://example.test/zakura.git"
revision = "short"
path = "../zakura"
required = true
""",
        """\
format_version = 1
[components.zakura]
repository = "https://example.test/zakura.git"
revision = "0123456789abcdef0123456789abcdef01234567"
upstream = "https://example.test/upstream.git"
path = "../zakura"
required = true
""",
    ],
)
def test_load_component_lock_rejects_malformed_configured_components(
    tmp_path: Path,
    content: str,
) -> None:
    lock_path = write_lock(tmp_path, content)

    with pytest.raises(component_lock.ComponentLockError):
        _ = component_lock.load_component_lock(lock_path)


@pytest.mark.parametrize(
    "content",
    [
        """\
format_version = 1
[components.gateway]
path = "../gateway"
required = false
repository = "https://example.test/gateway.git"
""",
        """\
format_version = 1
[components.gateway]
path = "../gateway"
required = true
""",
    ],
)
def test_load_component_lock_rejects_invalid_optional_components(
    tmp_path: Path,
    content: str,
) -> None:
    lock_path = write_lock(tmp_path, content)

    with pytest.raises(component_lock.ComponentLockError):
        _ = component_lock.load_component_lock(lock_path)


@pytest.mark.parametrize("path", ["component", "../../outside", "../nested/component"])
def test_load_component_lock_requires_adjacent_sibling_paths(tmp_path: Path, path: str) -> None:
    lock_path = write_lock(
        tmp_path,
        f'format_version = 1\n[components.gateway]\npath = "{path}"\nrequired = false\n',
    )

    with pytest.raises(component_lock.ComponentLockError, match="sibling"):
        _ = component_lock.load_component_lock(lock_path)


def test_load_component_lock_rejects_duplicate_canonical_paths(tmp_path: Path) -> None:
    lock_path = write_lock(
        tmp_path,
        """\
format_version = 1
[components.gateway]
path = "../gateway"
required = false

[components.wallet]
path = "../gateway/."
required = false
""",
    )

    with pytest.raises(component_lock.ComponentLockError, match="duplicate"):
        _ = component_lock.load_component_lock(lock_path)


def test_create_git_fixture_creates_two_distinct_commits(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)

    assert fixture.first_revision != fixture.second_revision
    assert len(fixture.first_revision) == REVISION_LENGTH
    assert len(fixture.second_revision) == REVISION_LENGTH
    assert (fixture.repository / "fixture.txt").read_text(encoding="utf-8") == "second revision\n"
