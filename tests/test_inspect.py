from __future__ import annotations

import subprocess
from pathlib import Path

from tests.git_fixture import create_git_fixture

BOOTSTRAP = Path(__file__).parents[1] / "scripts" / "bootstrap"
INSPECT = Path(__file__).parents[1] / "scripts" / "inspect"
STATUS = Path(__file__).parents[1] / "scripts" / "check-components"


def write_lock(root: Path, revision: str) -> Path:
    integration_root = root / "integration"
    integration_root.mkdir()
    _ = (integration_root / "components.lock.toml").write_text(
        f"""\
format_version = 1

[components.zakura]
repository = "{root / "component"}"
revision = "{revision}"
path = "../target"
required = true
""",
        encoding="utf-8",
    )
    return integration_root


def run(command: Path, integration_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(command)],
        cwd=integration_root,
        check=False,
        capture_output=True,
        text=True,
    )


def test_inspect_reports_status_and_wp00_boundary(tmp_path: Path) -> None:
    fixture = create_git_fixture(tmp_path)
    integration_root = write_lock(tmp_path, fixture.second_revision)
    _ = run(BOOTSTRAP, integration_root)

    inspected = run(INSPECT, integration_root)

    assert inspected.returncode == 0
    assert "name=zakura requirement=required state=healthy" in inspected.stdout
    assert "inspection_boundary=zakura_checkout_status" in inspected.stdout
    assert "end_to_end_service=absent" in inspected.stdout


def test_cli_reports_invalid_manifest_without_traceback(tmp_path: Path) -> None:
    integration_root = tmp_path / "integration"
    integration_root.mkdir()
    _ = (integration_root / "components.lock.toml").write_text(
        "format_version = 2\n",
        encoding="utf-8",
    )

    results = tuple(run(command, integration_root) for command in (BOOTSTRAP, STATUS, INSPECT))

    assert all(result.returncode == 1 for result in results)
    assert all("format_version" in result.stderr for result in results)
    assert all("Traceback" not in result.stderr for result in results)


def test_cli_reports_missing_manifest_without_traceback(tmp_path: Path) -> None:
    integration_root = tmp_path / "integration"
    integration_root.mkdir()

    results = tuple(run(command, integration_root) for command in (BOOTSTRAP, STATUS, INSPECT))

    assert all(result.returncode == 1 for result in results)
    assert all("components.lock.toml" in result.stderr for result in results)
    assert all("Traceback" not in result.stderr for result in results)
