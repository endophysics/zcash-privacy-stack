from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitFixture:
    repository: Path
    first_revision: str
    second_revision: str


def create_git_fixture(root: Path) -> GitFixture:
    repository = root / "component"
    repository.mkdir()
    _ = _git(repository, ("init", "--quiet"))
    _ = _git(repository, ("config", "user.name", "Component Fixture"))
    _ = _git(repository, ("config", "user.email", "fixture@example.test"))

    fixture_file = repository / "fixture.txt"
    _ = fixture_file.write_text("first revision\n", encoding="utf-8")
    _ = _git(repository, ("add", "fixture.txt"))
    _ = _git(repository, ("commit", "--quiet", "-m", "first revision"))
    first_revision = _git(repository, ("rev-parse", "HEAD"))

    _ = fixture_file.write_text("second revision\n", encoding="utf-8")
    _ = _git(repository, ("add", "fixture.txt"))
    _ = _git(repository, ("commit", "--quiet", "-m", "second revision"))
    second_revision = _git(repository, ("rev-parse", "HEAD"))
    return GitFixture(repository, first_revision, second_revision)


def _git(repository: Path, arguments: tuple[str, ...]) -> str:
    environment = dict(os.environ)
    environment["GIT_MASTER"] = "1"
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
