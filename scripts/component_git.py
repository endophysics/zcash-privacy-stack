"""Typed local Git queries used by component inspection."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path


GIT_NAME: Final = "git"


@dataclass(frozen=True, slots=True)
class GitQuery:
    """The successfulness and standard output of a local Git command."""

    succeeded: bool
    output: str


@dataclass(frozen=True, slots=True)
class GitCommand:
    """The complete result of a local non-shell Git command."""

    succeeded: bool
    output: str
    error: str


def run_git(directory: Path, arguments: tuple[str, ...]) -> GitCommand:
    """Run a PATH-resolved Git command with the repository tool marker."""
    executable = shutil.which(GIT_NAME)
    if executable is None:
        return GitCommand(succeeded=False, output="", error="git executable not found")
    environment = dict(os.environ)
    environment["GIT_MASTER"] = "1"
    completed = subprocess.run(
        [executable, *arguments],
        cwd=directory,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    return GitCommand(
        succeeded=completed.returncode == 0,
        output=completed.stdout.strip(),
        error=completed.stderr.strip(),
    )


def query_git(repository: Path, arguments: tuple[str, ...]) -> GitQuery:
    """Run a non-shell Git query in a component checkout."""
    command = run_git(repository, arguments)
    return GitQuery(succeeded=command.succeeded, output=command.output)


def is_git_repository(repository: Path) -> bool:
    """Return whether a path is a usable Git work tree."""
    query = query_git(repository, ("rev-parse", "--is-inside-work-tree"))
    return query.succeeded and query.output == "true"
