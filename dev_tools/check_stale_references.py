# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


@dataclass(frozen=True)
class StaleReference:
    """A reference in a tracked file that points to a deleted/renamed path."""

    file: str
    line: int
    deleted_path: str


def get_repo_root() -> str:
    return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()  # noqa: S607


def get_deleted_paths() -> list[str]:
    """Return repo-relative paths of files being deleted or renamed away in the staged commit."""
    output = subprocess.check_output(
        ["git", "diff", "--cached", "--diff-filter=DR", "--name-status"],  # noqa: S607
        text=True,
    )
    deleted: list[str] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if parts[0].startswith("D"):
            deleted.append(parts[1])
        elif parts[0].startswith("R"):
            # For renames, the old (now-gone) path is the second column
            deleted.append(parts[1])
    return deleted


def get_tracked_files() -> list[str]:
    """Return all files that will exist after the staged commit."""
    return subprocess.check_output(["git", "ls-files"], text=True).splitlines()  # noqa: S607


def build_path_patterns(deleted_paths: list[str]) -> dict[str, re.Pattern[str]]:
    """Build a regex per deleted path that matches references to it.

    For path "a/b/c.txt", matches (with non-word boundaries):
      - /?a/b/c.txt        (full path, optional leading /)
      - (../)*b/c.txt      (intermediate suffix with optional ../ prefix)
      - (../)*c.txt        (basename with optional ../ prefix)
    """
    patterns: dict[str, re.Pattern[str]] = {}
    for path in deleted_paths:
        segments = path.split("/")
        alternatives: list[str] = []
        for i in range(len(segments)):
            suffix = "/".join(segments[i:])
            escaped_suffix = re.escape(suffix)
            if i == 0:
                alternatives.append(rf"/?{escaped_suffix}")
            else:
                alternatives.append(rf"(?:\.\./)*{escaped_suffix}")
        patterns[path] = re.compile(rf"(?<!\w)(?:{'|'.join(alternatives)})(?!\w)")
    return patterns


def find_stale_references(
    tracked_files: list[str],
    deleted_paths: list[str],
    read_file: Callable[[str], str] | None = None,
) -> list[StaleReference]:
    """Search tracked files for references to deleted paths."""
    if not deleted_paths:
        return []

    path_patterns = build_path_patterns(deleted_paths)
    deleted_set = set(deleted_paths)
    stale: list[StaleReference] = []

    for filepath in tracked_files:
        if filepath in deleted_set:
            continue
        try:
            if read_file is not None:
                content = read_file(filepath)
            else:
                with Path(filepath).open(errors="replace") as f:
                    content = f.read()
        except OSError:
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            for deleted_path, pattern in path_patterns.items():
                if pattern.search(line):
                    stale.append(StaleReference(filepath, line_number, deleted_path))

    return stale


def print_stale_references(stale_refs: list[StaleReference]) -> None:
    print("Stale references to deleted/renamed files:")
    for ref in stale_refs:
        print(f"  {ref.file}:{ref.line} references {ref.deleted_path}")


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    deleted_paths = get_deleted_paths()
    if not deleted_paths:
        return 0

    tracked_files = get_tracked_files()

    if stale_refs := find_stale_references(tracked_files, deleted_paths):
        print_stale_references(stale_refs)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
