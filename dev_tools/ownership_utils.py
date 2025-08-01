# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

import re
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


class OwnerShipEntry:
    def __init__(self, pattern: str, owners: tuple[str, ...], line_number: int) -> None:
        self.pattern: str = pattern
        self.owners: tuple[str, ...] = owners
        self.line_number: int = line_number


class GithubOwnerShip:
    def __init__(self, repo_dir: Path) -> None:
        self._ownerships = parse_ownership(repo_dir / ".github" / "CODEOWNERS")
        self._repo_dir = repo_dir
        self._cached_regex = CachedRegex()

    def is_owned_by(self, file: Path, codeowner: str) -> bool:
        return codeowner in self.get_owners(file)

    def get_first_owner(self, file: Path) -> str | None:
        owners = self.get_owners(file)
        return owners[0] if owners else None

    def get_owners(self, file: Path) -> tuple[str, ...]:
        file_relative = file.relative_to(self._repo_dir)
        for ownership in self._ownerships:
            if self.is_file_covered_by_pattern(file_relative, ownership.pattern):
                return ownership.owners

        return ()

    @staticmethod
    def is_path_prefix(path: str, prefix: str) -> bool:
        """Check if `prefix` is one of the parents of `path`, including itself."""
        if not path.startswith(prefix):
            return False
        prefix_length = len(prefix)
        if len(path) == prefix_length:
            return True
        return path[prefix_length] == "/"

    def is_file_covered_by_pattern(self, filepath_in_repo: Path, pattern: str) -> bool:
        """Implements the complete featureset demonstrated at https://docs.github.com/en/repositories/managing-your-
        repositorys-settings-and-features/customizing-your-repository/about-code-owners#example-of-a-codeowners-file."""
        filepath_string = str(filepath_in_repo)
        if "*" in pattern:
            return self._match_pattern_with_asterisks(filepath_string, filepath_in_repo.name, pattern)
        if pattern.startswith("/"):
            return GithubOwnerShip.is_path_prefix(path=filepath_string, prefix=pattern[1:].rstrip("/"))
        return pattern.rstrip("/") in filepath_string

    def _match_pattern_with_asterisks(self, filepath_string: str, filename: str, pattern: str) -> bool:
        regex_pattern = pattern.replace("*", "(.*)")
        regex_pattern = regex_pattern[1:] if pattern.startswith("/") else f".*?{regex_pattern}"

        matches = self._cached_regex.match(regex_pattern, filepath_string)

        if pattern.endswith("/*"):
            return False if matches is None else bool(matches.groups()[-1] == filename)

        return matches is not None


class CachedRegex:
    """A wrapper around re.match to compile and cache regex patterns.

    It has unlimited size.
    """

    def __init__(self) -> None:
        self._cache: dict[str, re.Pattern[str]] = {}

    def match(self, needle: str, haystack: str, flags: int = 0) -> re.Match | None:
        if needle not in self._cache:
            self._cache[needle] = re.compile(needle, flags)
        return self._cache[needle].match(haystack)


def parse_ownership(codeowners_file: Path) -> tuple[OwnerShipEntry, ...]:
    """Return ownership in reverse order.

    Order is important. Last matching pattern in CODEOWNERS takes the most
    precedence.
    """
    return tuple(reversed(tuple(get_ownership_entries(codeowners_file))))


def get_ownership_entries(codeowners_file: Path) -> Generator[OwnerShipEntry]:
    with codeowners_file.open() as file:
        for line_number, line in enumerate(file.readlines(), start=1):
            current_line = line.strip()

            if current_line.startswith("#"):  # comment
                continue

            match = re.findall(r"(\S+)", current_line)
            if match:
                yield OwnerShipEntry(match[0], tuple(match[1:]), line_number)


def check_git(command: str, repo_dir: Path) -> str:
    return subprocess.check_output(f"git {command}".split(), cwd=repo_dir).decode(sys.stdout.encoding)
