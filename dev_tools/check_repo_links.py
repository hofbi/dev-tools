# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

"""Verify that ``@repo`` relative links in text files point to existing files or directories."""

from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from dev_tools.utils.git_hook_utils import parse_arguments

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

# The marker must not be preceded by a word character or another ``@`` (so ``@report``, ``foo@repo``
# and ``@@repo`` never match) and must be followed by same-line whitespace and a non-whitespace path.
# Requiring whitespace (rather than any delimiter) avoids the common npm/pnpm scope ``@repo/...``.
MARKER = re.compile(rb"(?<![\w@])@repo[ \t]+(\S+)")

# Trailing punctuation that is almost never part of a real path and usually comes from prose or
# enclosing syntax, e.g. "see @repo foo.md." or "(@repo foo.md)".
_TRAILING_PUNCTUATION = ".,;:!?)\"'`]}>"


class BrokenLink(NamedTuple):
    """A relative ``@repo`` link that does not resolve to a tracked file or directory."""

    file_path: str
    line: int
    column: int
    link: str


def resolve_link_target(link: str, file_path: str) -> str | None:
    """Resolve a raw ``@repo`` link to a repo-root-relative path, or None if it should be skipped.

    Links starting with ``/`` are resolved from the repository root, everything else relative to the
    file the link appears in. URLs, mailto links and anchor-only targets are skipped.
    """
    link = link.split("#", 1)[0].split("?", 1)[0].rstrip(_TRAILING_PUNCTUATION)
    if not link or "://" in link or link.startswith("mailto:"):
        return None
    if link.startswith("/"):
        return posixpath.normpath(link[1:])
    return posixpath.normpath(posixpath.join(posixpath.dirname(file_path), link))


def offset_to_line_and_column(content: bytes, offset: int) -> tuple[int, int]:
    """Return the 1-based (line, column) of a byte offset within content."""
    line = content.count(b"\n", 0, offset) + 1
    column = offset - content.rfind(b"\n", 0, offset)
    return line, column


def find_broken_links_in_content(
    content: bytes,
    file_path: str,
    does_target_exist: Callable[[str], bool],
) -> list[BrokenLink]:
    """Scan a single file's bytes and return the broken ``@repo`` links it contains."""
    # Fast pre-filter: skip the overwhelming majority of files without running the regex.
    if b"@repo" not in content:
        return []
    broken_links: list[BrokenLink] = []
    for match in MARKER.finditer(content):
        link = match.group(1).decode("utf-8", errors="replace")
        target = resolve_link_target(link, file_path)
        if target is None or does_target_exist(target):
            continue
        # Only for a confirmed broken link do we pay for computing the precise location.
        line, column = offset_to_line_and_column(content, match.start(1))
        broken_links.append(BrokenLink(file_path, line, column, link))
    return broken_links


def find_broken_links(
    files_to_check: list[Path],
    repository_root: Path,
    does_target_exist: Callable[[str], bool],
) -> list[BrokenLink]:
    broken_links: list[BrokenLink] = []
    for file in files_to_check:
        repo_relative_path = file.resolve().relative_to(repository_root).as_posix()
        broken_links.extend(find_broken_links_in_content(file.read_bytes(), repo_relative_path, does_target_exist))
    return broken_links


def build_set_of_valid_link_targets(tracked_files: Iterable[str]) -> set[str]:
    """Build the set of valid link targets: every tracked file plus all of their parent directories."""
    valid_targets = set(tracked_files)
    for path in list(valid_targets):
        parent = posixpath.dirname(path)
        while parent:
            valid_targets.add(parent)
            parent = posixpath.dirname(parent)
    valid_targets.add(".")  # the repository root itself
    return valid_targets


def get_repository_root() -> Path:
    output = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],  # noqa: S607
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    return Path(output.strip())


def list_tracked_files(repository_root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "-C", str(repository_root), "ls-files", "-z"],  # noqa: S607
        capture_output=True,
        check=True,
    ).stdout
    return [path.decode("utf-8", "surrogateescape") for path in output.split(b"\0") if path]


def print_broken_links(broken_links: list[BrokenLink]) -> None:
    if not broken_links:
        return
    print("Found broken links:")
    for link in broken_links:
        print(f"{link.file_path}:{link.line}:{link.column} {link.link}")


def main(argv: Sequence[str] | None = None) -> int:
    files = parse_arguments(argv).filenames
    repository_root = get_repository_root()
    does_target_exist = build_set_of_valid_link_targets(list_tracked_files(repository_root)).__contains__
    broken_links = find_broken_links(files, repository_root, does_target_exist)
    print_broken_links(broken_links)
    return 1 if broken_links else 0


if __name__ == "__main__":
    sys.exit(main())
