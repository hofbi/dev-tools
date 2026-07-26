# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

"""Verify that ``@repo`` relative links in text files point to existing files or directories."""

from __future__ import annotations

import contextlib
import posixpath
import re
import subprocess
import sys
from typing import TYPE_CHECKING, NamedTuple

from dev_tools.utils.git_hook_utils import parse_arguments

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from pathlib import Path

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
        base, relative = "", link[1:]
    else:
        base, relative = posixpath.dirname(file_path), link
    return posixpath.normpath(posixpath.join(base, relative))


def offset_to_line_and_column(content: bytes, offset: int) -> tuple[int, int]:
    """Return the 1-based (line, column) of a byte offset within content."""
    line = content.count(b"\n", 0, offset) + 1
    column = offset - content.rfind(b"\n", 0, offset)
    return line, column


def find_broken_links_in_content(
    content: bytes,
    file_path: str,
    target_exists: Callable[[str], bool],
) -> list[BrokenLink]:
    """Scan a single file's bytes and return the broken ``@repo`` links it contains."""
    # Fast pre-filter: skip the overwhelming majority of files without running the regex.
    if b"@repo" not in content:
        return []
    broken: list[BrokenLink] = []
    for match in MARKER.finditer(content):
        link = match.group(1).decode("utf-8", errors="replace")
        target = resolve_link_target(link, file_path)
        if target is None or target_exists(target):
            continue
        # Only for a confirmed broken link do we pay for computing the precise location.
        line, column = offset_to_line_and_column(content, match.start(1))
        broken.append(BrokenLink(file_path, line, column, link))
    return broken


def find_broken_links(files: list[Path], target_exists: Callable[[str], bool]) -> list[BrokenLink]:
    broken: list[BrokenLink] = []
    for file in files:
        with contextlib.suppress(OSError):
            broken.extend(find_broken_links_in_content(file.read_bytes(), file.as_posix(), target_exists))
    return broken


def build_valid_target_set(tracked_files: Iterable[str]) -> set[str]:
    """Build the set of valid link targets: every tracked file plus all of their parent directories."""
    valid = set(tracked_files)
    for path in list(valid):
        parent = posixpath.dirname(path)
        while parent:
            valid.add(parent)
            parent = posixpath.dirname(parent)
    valid.add(".")  # the repository root itself
    return valid


def list_tracked_files() -> list[str]:
    output = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout  # noqa: S607
    return [path.decode("utf-8", "surrogateescape") for path in output.split(b"\0") if path]


def report_broken_links(broken: list[BrokenLink]) -> bool:
    if not broken:
        return False
    print("Found broken links:")
    for link in broken:
        print(f"{link.file_path}:{link.line}:{link.column} {link.link}")
    return True


def main(argv: Sequence[str] | None = None) -> int:
    files = parse_arguments(argv).filenames
    target_exists = build_valid_target_set(list_tracked_files()).__contains__
    return 1 if report_broken_links(find_broken_links(files, target_exists)) else 0


if __name__ == "__main__":
    sys.exit(main())
