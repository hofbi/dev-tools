# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class StaleReference:
    """A reference in a tracked file that points to a deleted/renamed path."""

    file: str
    line: int
    deleted_path: str

    def __str__(self) -> str:
        """Format as file:line references deleted_path."""
        return f"{self.file}:{self.line} references {self.deleted_path}"


def _run_git(*args: str, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=check,
    ).stdout


def get_deleted_paths() -> list[str]:
    """Return repo-relative paths of files being deleted or renamed away in the staged commit."""
    output = _run_git("diff", "--cached", "--diff-filter=DR", "--name-status")
    # Both D(eleted) and R(enamed) have the vanishing path in column 1
    return [line.split("\t")[1] for line in output.splitlines()]


def build_path_pattern(deleted_path: str) -> str:
    """Build a PCRE pattern for a deleted path that matches references to it.

    For path "a/b/c.txt", matches (with non-word/dot/dash boundaries):
      - /?a/b/c.txt        (full path, optional leading /)
      - (../)*b/c.txt      (intermediate suffix with optional ../ prefix)
      - (../)*c.txt        (basename with optional ../ prefix)
    """
    segments = deleted_path.split("/")
    alternatives: list[str] = []
    for i in range(len(segments)):
        suffix = "/".join(segments[i:])
        escaped_suffix = re.escape(suffix)
        if i == 0:
            alternatives.append(rf"/?{escaped_suffix}")
        else:
            alternatives.append(rf"(?:\.\./)*{escaped_suffix}")
    return rf"(?<![\w.-])(?:{'|'.join(alternatives)})(?![\w.-])"


def git_grep(pattern: str) -> list[tuple[str, int]]:
    """Run git grep with PCRE and return (file, line_number) tuples."""
    output = _run_git("grep", "-nP", pattern, check=False)
    matches: list[tuple[str, int]] = []
    for line in output.splitlines():
        file, line_no, _text = line.split(":", 2)
        matches.append((file, int(line_no)))
    return matches


def find_stale_references(deleted_paths: list[str]) -> list[StaleReference]:
    """Search tracked files for references to deleted paths."""
    deleted_set = set(deleted_paths)
    stale: list[StaleReference] = []

    for deleted_path in deleted_paths:
        pattern = build_path_pattern(deleted_path)

        for file, line_no in git_grep(pattern):
            if file in deleted_set:
                continue
            stale.append(StaleReference(file, line_no, deleted_path))

    return stale


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    deleted_paths = get_deleted_paths()

    if stale_refs := find_stale_references(deleted_paths):
        print("Stale references to deleted/renamed files:")
        for ref in stale_refs:
            print(f"  {ref}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
