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


def _run_git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def get_deleted_paths() -> list[str]:
    """Return repo-relative paths of files being deleted or renamed away in the staged commit."""
    output = _run_git("diff", "--cached", "--diff-filter=DR", "--name-status")
    # Both D(eleted) and R(enamed) have the vanishing path in column 1
    return [line.split("\t")[1] for line in output.splitlines()]


def build_path_pattern(deleted_path: str) -> re.Pattern[str]:
    """Build a regex for a deleted path that matches references to it.

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
    return re.compile(rf"(?<![\w.-])(?:{'|'.join(alternatives)})(?![\w.-])")


def git_grep(pattern: str) -> list[tuple[str, int, str]]:
    """Run git grep and return (file, line_number, line_text) tuples."""
    result = subprocess.run(
        ["git", "grep", "-nE", pattern],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    matches: list[tuple[str, int, str]] = []
    for line in result.stdout.splitlines():
        # git grep output: file:line_number:matched_line
        file, line_no, text = line.split(":", 2)
        matches.append((file, int(line_no), text))
    return matches


def find_stale_references(deleted_paths: list[str]) -> list[StaleReference]:
    """Search tracked files for references to deleted paths using git grep."""
    if not deleted_paths:
        return []

    deleted_set = set(deleted_paths)
    stale: list[StaleReference] = []

    for deleted_path in deleted_paths:
        pattern = build_path_pattern(deleted_path)
        # Build a git grep ERE from the path suffixes (unanchored, case-sensitive)
        segments = deleted_path.split("/")
        suffixes = ["/".join(segments[i:]) for i in range(len(segments))]
        grep_pattern = "|".join(re.escape(s) for s in suffixes)

        for file, line_no, text in git_grep(grep_pattern):
            if file in deleted_set:
                continue
            if pattern.search(text):
                stale.append(StaleReference(file, line_no, deleted_path))

    return stale


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    deleted_paths = get_deleted_paths()
    if not deleted_paths:
        return 0

    if stale_refs := find_stale_references(deleted_paths):
        print("Stale references to deleted/renamed files:")
        for ref in stale_refs:
            print(f"  {ref}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
