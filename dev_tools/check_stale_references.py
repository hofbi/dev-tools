from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass

BUILD_FILE_NAMES = frozenset({"BUILD", "BUILD.bazel", "CMakeLists.txt", "Makefile", "meson.build", "WORKSPACE"})
BUILD_FILE_EXTENSIONS = frozenset({"bzl", "bazel", "cmake", "mk", "gradle", "gn", "gni"})

# A single-segment path carries no more information than its bare file name.
MIN_SEGMENTS_FOR_FULL_PATH = 2

# Changelogs describe what the repository looked like in the past, so a vanished path belongs there.
CHANGELOG_FILE = re.compile(r"change[-_]?log|release[-_]?notes|releases|history|news", re.IGNORECASE)

# Escape hatch for the cases the heuristic cannot know about, such as documentation
# describing a file the reader is meant to create.
NOLINT_MARKER = "nolint(stale_references)"

# Includes and imports are already validated by the compiler, interpreter, or build system.
TOOL_CHECKED_LINE = re.compile(
    r"""^\s*(
        \#\s*(include|import)\b
        | (from\s+\S+\s+)?import\b
        | \}\s*from\s+['"]
        | load\s*\(
        | (const|let|var)\s+.*\brequire\s*\(
    )""",
    re.VERBOSE,
)
COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*|;|<!--|--)")


@dataclass(frozen=True)
class StaleReference:
    """A reference in a tracked file that points to a deleted/renamed path."""

    from_file: str
    from_line: int
    to_path: str

    def __str__(self) -> str:
        """Format as file:line references deleted_path."""
        return f"{self.from_file}:{self.from_line} references {self.to_path}"


def _run_git(*args: str, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=check,
    ).stdout


def get_deleted_paths() -> set[str]:
    """Return repo-relative paths of files being deleted or renamed away in the staged commit."""
    output = _run_git("diff", "--cached", "--diff-filter=DR", "--name-status")
    # Both D(eleted) and R(enamed) have the vanishing path in column 1
    return {line.split("\t")[1] for line in output.splitlines()}


def get_tracked_paths() -> list[str]:
    """Return repo-relative paths of all tracked files."""
    return _run_git("ls-files").splitlines()


def build_path_pattern(deleted_path: str, *, basename_is_unique: bool) -> str | None:
    """Build a PCRE pattern matching references to a deleted path, or None if nothing is specific enough.

    Only two forms carry enough signal to report:
      - the full path, when it has at least two segments (a root-level path is only a basename)
      - the bare basename, when it has an extension and no surviving file shares it

    Intermediate suffixes such as "b/c.txt" are deliberately not matched: repeated directory
    layouts like "modules/main/main.tf" make them match a parallel subtree far more often than
    the intended file.
    """
    segments = deleted_path.split("/")
    basename = segments[-1]
    alternatives = []
    if len(segments) >= MIN_SEGMENTS_FOR_FULL_PATH:
        alternatives.append(re.escape(deleted_path))
    if basename_is_unique and "." in basename:
        alternatives.append(re.escape(basename))
    if not alternatives:
        return None
    return rf"(?<![\w.-])(?:{'|'.join(alternatives)})(?![\w.-])"


def git_grep(pattern: str) -> list[tuple[str, int, str]]:
    """Run git grep with PCRE and return (file, line_number, line_text) tuples."""
    output = _run_git("grep", "-nIP", pattern, check=False)
    matches = []
    for line in output.splitlines():
        file, line_no, text = line.split(":", 2)
        matches.append((file, int(line_no), text))
    return matches


def is_reportable(hit_file: str, line_text: str) -> bool:
    """Report only references that no other tool already verifies."""
    name = hit_file.rsplit("/", 1)[-1]
    if NOLINT_MARKER in line_text or CHANGELOG_FILE.search(name) or TOOL_CHECKED_LINE.match(line_text):
        return False
    is_build_file = (
        name in BUILD_FILE_NAMES or name.startswith("Makefile") or name.rsplit(".", 1)[-1] in BUILD_FILE_EXTENSIONS
    )
    return not (is_build_file and not COMMENT_LINE.match(line_text))


def find_stale_references() -> list[StaleReference]:
    """Search tracked files for references to deleted paths, at most one per referencing file."""
    deleted_paths = get_deleted_paths()
    if not deleted_paths:
        return []

    surviving = Counter(path.rsplit("/", 1)[-1] for path in get_tracked_paths() if path not in deleted_paths)

    references = []
    for deleted_path in sorted(deleted_paths):
        pattern = build_path_pattern(
            deleted_path,
            basename_is_unique=surviving[deleted_path.rsplit("/", 1)[-1]] == 0,
        )
        if pattern is None:
            continue
        already_reported: set[str] = set()
        for file, line_no, text in git_grep(pattern):
            if file in deleted_paths or file in already_reported or not is_reportable(file, text):
                continue
            already_reported.add(file)
            references.append(StaleReference(from_file=file, from_line=line_no, to_path=deleted_path))
    return references


def main() -> int:
    if stale_refs := find_stale_references():
        print("Stale references to deleted/renamed files:")
        for ref in stale_refs:
            print(f"  {ref}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
