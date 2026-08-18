from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from tests.git_fixture import create_git_fixture

BOOTSTRAP = Path(__file__).parents[1] / "scripts" / "bootstrap"
CHECK_COMPONENTS = Path(__file__).parents[1] / "scripts" / "check-components"


@dataclass(frozen=True, slots=True)
class LockSpec:
    repository: Path
    revision: str
    required: str
    upstream: str | None


def write_configured_lock(root: Path, spec: LockSpec) -> Path:
    integration_root = root / "integration"
    integration_root.mkdir(exist_ok=True)
    upstream_fields = ""
    if spec.upstream is not None:
        upstream_fields = f'upstream = "{spec.upstream}"\nupstream_base = "{spec.revision}"\n'
    lock_path = integration_root / "components.lock.toml"
    _ = lock_path.write_text(
        f"""\
format_version = 1

[components.component]
repository = "{spec.repository}"
{upstream_fields}revision = "{spec.revision}"
path = "../target"
required = {spec.required}
""",
        encoding="utf-8",
    )
    return integration_root


def write_optional_lock(root: Path) -> Path:
    integration_root = root / "integration"
    integration_root.mkdir()
    _ = (integration_root / "components.lock.toml").write_text(
        'format_version = 1\n[components.optional]\npath = "../optional"\nrequired = false\n',
        encoding="utf-8",
    )
    return integration_root


def run_command(command: Path, integration_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(command)],
        cwd=integration_root,
        check=False,
        capture_output=True,
        text=True,
    )


def head_revision(root: Path) -> str:
    return (target(root) / ".git" / "HEAD").read_text(encoding="utf-8").strip()


def target(root: Path) -> Path:
    return root / "target"


def test_bootstrap_clones_detaches_and_leaves_status_healthy(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    integration_root = write_configured_lock(
        tmp_path,
        LockSpec(fixture.repository, fixture.first_revision, "true", None),
    )

    bootstrap = run_command(BOOTSTRAP, integration_root)
    status = run_command(CHECK_COMPONENTS, integration_root)

    assert bootstrap.returncode == 0
    assert "action=cloned" in bootstrap.stdout
    assert (target(tmp_path) / ".git").exists()
    assert head_revision(tmp_path) == fixture.first_revision
    assert status.returncode == 0
    assert "state=healthy" in status.stdout


def test_bootstrap_second_run_is_idempotent(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    integration_root = write_configured_lock(
        tmp_path,
        LockSpec(fixture.repository, fixture.second_revision, "true", None),
    )

    _ = run_command(BOOTSTRAP, integration_root)
    repeated = run_command(BOOTSTRAP, integration_root)

    assert repeated.returncode == 0
    assert "action=current" in repeated.stdout


def test_bootstrap_normalizes_uppercase_pin_for_status_and_idempotency(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    integration_root = write_configured_lock(
        tmp_path,
        LockSpec(fixture.repository, fixture.second_revision.upper(), "true", None),
    )

    first = run_command(BOOTSTRAP, integration_root)
    repeated = run_command(BOOTSTRAP, integration_root)
    status = run_command(CHECK_COMPONENTS, integration_root)

    assert first.returncode == 0
    assert repeated.returncode == 0
    assert "action=current" in repeated.stdout
    assert status.returncode == 0
    assert "state=healthy" in status.stdout


def test_bootstrap_updates_clean_checkout_to_new_pin(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    first = LockSpec(fixture.repository, fixture.first_revision, "true", None)
    integration_root = write_configured_lock(tmp_path, first)
    _ = run_command(BOOTSTRAP, integration_root)
    second = LockSpec(fixture.repository, fixture.second_revision, "true", None)
    integration_root = write_configured_lock(tmp_path, second)

    updated = run_command(BOOTSTRAP, integration_root)

    assert updated.returncode == 0
    assert "action=updated" in updated.stdout
    assert head_revision(tmp_path) == fixture.second_revision


def test_bootstrap_refuses_dirty_checkout_without_mutation(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    integration_root = write_configured_lock(
        tmp_path,
        LockSpec(fixture.repository, fixture.first_revision, "true", None),
    )
    _ = run_command(BOOTSTRAP, integration_root)
    file_path = target(tmp_path) / "fixture.txt"
    _ = file_path.write_text("dirty\n", encoding="utf-8")
    integration_root = write_configured_lock(
        tmp_path,
        LockSpec(fixture.repository, fixture.second_revision, "true", None),
    )

    refused = run_command(BOOTSTRAP, integration_root)

    assert refused.returncode == 1
    assert "dirty" in refused.stderr
    assert file_path.read_text(encoding="utf-8") == "dirty\n"
    assert head_revision(tmp_path) == fixture.first_revision


def test_bootstrap_refuses_invalid_existing_path(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    target(tmp_path).mkdir()
    integration_root = write_configured_lock(
        tmp_path,
        LockSpec(fixture.repository, fixture.second_revision, "true", None),
    )

    refused = run_command(BOOTSTRAP, integration_root)

    assert refused.returncode == 1
    assert "not a Git worktree" in refused.stderr


def test_bootstrap_refuses_misconfigured_remotes(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    integration_root = write_configured_lock(
        tmp_path,
        LockSpec(
            fixture.repository, fixture.second_revision, "true", "https://expected.test/upstream"
        ),
    )
    _ = run_command(BOOTSTRAP, integration_root)
    config_path = target(tmp_path) / ".git" / "config"
    original = config_path.read_text(encoding="utf-8")
    _ = config_path.write_text(
        original.replace(str(fixture.repository), "https://wrong.test/origin"),
        encoding="utf-8",
    )

    origin_refusal = run_command(BOOTSTRAP, integration_root)
    _ = config_path.write_text(
        original.replace("https://expected.test/upstream", "https://wrong.test/upstream"),
        encoding="utf-8",
    )
    upstream_refusal = run_command(BOOTSTRAP, integration_root)

    assert origin_refusal.returncode == 1
    assert "origin URL" in origin_refusal.stderr
    assert upstream_refusal.returncode == 1
    assert "upstream URL" in upstream_refusal.stderr


def test_bootstrap_skips_unconfigured_optional_and_bootstraps_configured_optional(
    tmp_path: Path,
) -> None:
    optional_root = tmp_path / "optional"
    optional_root.mkdir()
    optional_integration = write_optional_lock(optional_root)
    skipped = run_command(BOOTSTRAP, optional_integration)
    fixture_root = tmp_path / "configured"
    fixture_root.mkdir()
    fixture = create_git_fixture(fixture_root)
    integration_root = write_configured_lock(
        fixture_root,
        LockSpec(fixture.repository, fixture.second_revision, "false", None),
    )

    configured = run_command(BOOTSTRAP, integration_root)

    assert skipped.returncode == 0
    assert "action=skipped" in skipped.stdout
    assert not (optional_root / "optional").exists()
    assert configured.returncode == 0
    assert "action=cloned" in configured.stdout
    assert head_revision(fixture_root) == fixture.second_revision
