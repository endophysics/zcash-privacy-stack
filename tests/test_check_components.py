from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tests.git_fixture import GitFixture, create_git_fixture

CHECK_COMPONENTS = Path(__file__).parents[1] / "scripts" / "check-components"
MISMATCHED_REVISION = "0" * 40
EXPECTED_UPSTREAM = "https://example.test/upstream.git"


def write_lock(
    root: Path,
    revision: str,
    upstream: str | None,
) -> Path:
    integration_root = root / "integration"
    integration_root.mkdir()
    upstream_fields = ""
    if upstream is not None:
        upstream_fields = f'upstream = "{upstream}"\nupstream_base = "{revision}"\n'
    optional_component = """
[components.optional]
path = "../optional"
required = false
"""
    lock_path = integration_root / "components.lock.toml"
    _ = lock_path.write_text(
        f"""\
format_version = 1

[components.component]
repository = "https://example.test/component.git"
{upstream_fields}revision = "{revision}"
path = "../component"
required = true
{optional_component}""",
        encoding="utf-8",
    )
    return integration_root


def run_check(integration_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CHECK_COMPONENTS)],
        cwd=integration_root,
        check=False,
        capture_output=True,
        text=True,
    )


def add_upstream(fixture: GitFixture, url: str) -> None:
    environment = dict(os.environ)
    environment["GIT_MASTER"] = "1"
    completed = subprocess.run(
        ["/usr/bin/git", "remote", "add", "upstream", url],
        cwd=fixture.repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    _ = completed


def git_action(fixture: GitFixture, arguments: tuple[str, ...]) -> None:
    environment = dict(os.environ)
    environment["GIT_MASTER"] = "1"
    completed = subprocess.run(
        ["/usr/bin/git", *arguments],
        cwd=fixture.repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    _ = completed


def write_configured_optional_lock(root: Path, revision: str) -> Path:
    integration_root = root / "integration"
    integration_root.mkdir()
    lock_path = integration_root / "components.lock.toml"
    _ = lock_path.write_text(
        f"""\
format_version = 1

[components.component]
repository = "https://example.test/component.git"
upstream = "{EXPECTED_UPSTREAM}"
revision = "{revision}"
upstream_base = "{revision}"
path = "../component"
required = false
""",
        encoding="utf-8",
    )
    return integration_root


def test_check_components_reports_healthy_required_and_absent_optional(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    git_action(fixture, ("checkout", "--detach", fixture.second_revision))
    git_action(fixture, ("remote", "add", "origin", "https://example.test/component.git"))
    add_upstream(fixture, EXPECTED_UPSTREAM)
    integration_root = write_lock(tmp_path, fixture.second_revision, EXPECTED_UPSTREAM)

    completed = run_check(integration_root)

    lines = completed.stdout.splitlines()
    assert completed.returncode == 0
    assert lines[0] == (
        f"name=component requirement=required state=healthy path={fixture.repository} "
        f"expected_revision={fixture.second_revision} current_revision={fixture.second_revision} "
        "expected_origin=https://example.test/component.git "
        "actual_origin=https://example.test/component.git head=detached "
        f"dirty=clean expected_upstream={EXPECTED_UPSTREAM} actual_upstream={EXPECTED_UPSTREAM}"
    )
    assert lines[1] == (
        f"name=optional requirement=optional state=absent path={tmp_path / 'optional'} "
        "expected_revision=unconfigured current_revision=absent "
        "expected_origin=unconfigured actual_origin=absent head=unknown dirty=unknown "
        "expected_upstream=unconfigured actual_upstream=absent"
    )


def test_check_components_fails_for_wrong_origin_at_exact_detached_pin(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    git_action(fixture, ("checkout", "--detach", fixture.second_revision))
    git_action(fixture, ("remote", "add", "origin", "https://wrong.test/component.git"))
    integration_root = write_lock(tmp_path, fixture.second_revision, None)

    completed = run_check(integration_root)

    assert completed.returncode == 1
    assert "state=origin_mismatch" in completed.stdout


def test_check_components_fails_for_attached_head_at_exact_pin(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    git_action(fixture, ("remote", "add", "origin", "https://example.test/component.git"))
    integration_root = write_lock(tmp_path, fixture.second_revision, None)

    completed = run_check(integration_root)

    assert completed.returncode == 1
    assert "state=attached_head" in completed.stdout


def test_check_components_allows_absent_configured_optional_component(tmp_path: Path) -> None:
    integration_root = write_configured_optional_lock(tmp_path, MISMATCHED_REVISION)

    completed = run_check(integration_root)

    assert completed.returncode == 0
    assert completed.stdout == (
        f"name=component requirement=optional state=absent path={tmp_path / 'component'} "
        f"expected_revision={MISMATCHED_REVISION} current_revision=absent "
        "expected_origin=https://example.test/component.git actual_origin=absent head=unknown "
        "dirty=unknown "
        f"expected_upstream={EXPECTED_UPSTREAM} actual_upstream=absent\n"
    )


def test_check_components_fails_for_mismatched_configured_optional_component(
    tmp_path: Path,
) -> None:
    _ = create_git_fixture(tmp_path)
    integration_root = write_configured_optional_lock(tmp_path, MISMATCHED_REVISION)

    completed = run_check(integration_root)

    assert completed.returncode == 1
    assert "requirement=optional state=revision_mismatch" in completed.stdout


def test_check_components_fails_for_dirty_configured_optional_component(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    _ = (fixture.repository / "fixture.txt").write_text("dirty\n", encoding="utf-8")
    integration_root = write_configured_optional_lock(tmp_path, fixture.second_revision)

    completed = run_check(integration_root)

    assert completed.returncode == 1
    assert "requirement=optional state=dirty" in completed.stdout


def test_check_components_fails_for_invalid_configured_optional_component(tmp_path: Path) -> None:
    component_path = tmp_path / "component"
    component_path.mkdir()
    integration_root = write_configured_optional_lock(tmp_path, MISMATCHED_REVISION)

    completed = run_check(integration_root)

    assert completed.returncode == 1
    assert "requirement=optional state=invalid_repository" in completed.stdout


def test_check_components_fails_for_broken_upstream_on_configured_optional_component(
    tmp_path: Path,
) -> None:
    fixture = create_git_fixture(tmp_path)
    git_action(fixture, ("checkout", "--detach", fixture.second_revision))
    git_action(fixture, ("remote", "add", "origin", "https://example.test/component.git"))
    integration_root = write_configured_optional_lock(tmp_path, fixture.second_revision)

    absent = run_check(integration_root)
    add_upstream(fixture, "https://example.test/different.git")
    mismatched = run_check(integration_root)

    assert absent.returncode == 1
    assert "requirement=optional state=upstream_absent" in absent.stdout
    assert mismatched.returncode == 1
    assert "requirement=optional state=upstream_mismatch" in mismatched.stdout


def test_check_components_fails_for_required_revision_mismatch(tmp_path: Path) -> None:
    _ = create_git_fixture(tmp_path)
    integration_root = write_lock(tmp_path, MISMATCHED_REVISION, None)

    completed = run_check(integration_root)

    assert completed.returncode == 1
    assert "state=revision_mismatch" in completed.stdout
    assert f"expected_revision={MISMATCHED_REVISION}" in completed.stdout


def test_check_components_fails_for_required_dirty_tree(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    _ = (fixture.repository / "fixture.txt").write_text("dirty\n", encoding="utf-8")
    integration_root = write_lock(tmp_path, fixture.second_revision, None)

    completed = run_check(integration_root)

    assert completed.returncode == 1
    assert "state=dirty" in completed.stdout
    assert "dirty=dirty" in completed.stdout


def test_check_components_fails_for_missing_or_mismatched_upstream(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    git_action(fixture, ("checkout", "--detach", fixture.second_revision))
    git_action(fixture, ("remote", "add", "origin", "https://example.test/component.git"))
    integration_root = write_lock(tmp_path, fixture.second_revision, EXPECTED_UPSTREAM)

    absent = run_check(integration_root)
    add_upstream(fixture, "https://example.test/different.git")
    mismatched = run_check(integration_root)

    assert absent.returncode == 1
    assert "state=upstream_absent" in absent.stdout
    assert mismatched.returncode == 1
    assert "state=upstream_mismatch" in mismatched.stdout


def test_check_components_fails_for_missing_or_invalid_required_component(tmp_path: Path) -> None:
    integration_root = write_lock(tmp_path, MISMATCHED_REVISION, None)

    absent = run_check(integration_root)
    component_path = tmp_path / "component"
    component_path.mkdir()
    invalid = run_check(integration_root)

    assert absent.returncode == 1
    assert "state=absent" in absent.stdout
    assert invalid.returncode == 1
    assert "state=invalid_repository" in invalid.stdout
