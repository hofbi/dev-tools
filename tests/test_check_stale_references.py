# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

from typing import TYPE_CHECKING

from dev_tools.check_stale_references import (
    StaleReference,
    build_path_patterns,
    find_stale_references,
    print_stale_references,
)

if TYPE_CHECKING:
    import pytest


def make_reader(files: dict[str, str]):
    def read_file(path: str) -> str:
        return files[path]

    return read_file


class TestBuildPathPatterns:
    def test_matches_full_path(self) -> None:
        patterns = build_path_patterns(["src/lib/foo.hpp"])
        assert patterns["src/lib/foo.hpp"].search("see src/lib/foo.hpp for details")

    def test_matches_full_path_with_leading_slash(self) -> None:
        patterns = build_path_patterns(["src/lib/foo.hpp"])
        assert patterns["src/lib/foo.hpp"].search("see /src/lib/foo.hpp for details")

    def test_matches_intermediate_suffix(self) -> None:
        patterns = build_path_patterns(["src/lib/foo.hpp"])
        assert patterns["src/lib/foo.hpp"].search("see lib/foo.hpp here")

    def test_matches_intermediate_suffix_with_dotdot(self) -> None:
        patterns = build_path_patterns(["src/lib/foo.hpp"])
        assert patterns["src/lib/foo.hpp"].search("see ../lib/foo.hpp here")

    def test_matches_basename(self) -> None:
        patterns = build_path_patterns(["src/lib/foo.hpp"])
        assert patterns["src/lib/foo.hpp"].search("see foo.hpp for details")

    def test_matches_basename_with_dotdot(self) -> None:
        patterns = build_path_patterns(["src/lib/foo.hpp"])
        assert patterns["src/lib/foo.hpp"].search("see ../../foo.hpp for details")

    def test_no_substring_match(self) -> None:
        patterns = build_path_patterns(["src/lib/foo.hpp"])
        assert not patterns["src/lib/foo.hpp"].search("notfoo.hpp")


class TestFindStaleReferences:
    def test_finds_reference_to_deleted_file(self) -> None:
        files = {
            "src/main.cpp": "// see src/utils/helper.hpp for details",
        }
        result = find_stale_references(
            list(files.keys()),
            ["src/utils/helper.hpp"],
            read_file=make_reader(files),
        )
        assert result == [StaleReference("src/main.cpp", 1, "src/utils/helper.hpp")]

    def test_no_reference_no_finding(self) -> None:
        files = {
            "src/main.cpp": "// nothing relevant here",
        }
        result = find_stale_references(
            list(files.keys()),
            ["src/utils/helper.hpp"],
            read_file=make_reader(files),
        )
        assert result == []

    def test_skips_deleted_file_itself(self) -> None:
        files = {
            "src/utils/helper.hpp": "#include helper.hpp",
            "src/main.cpp": "no reference",
        }
        result = find_stale_references(
            list(files.keys()),
            ["src/utils/helper.hpp"],
            read_file=make_reader(files),
        )
        assert result == []

    def test_empty_deleted_paths_returns_empty(self) -> None:
        assert find_stale_references(["a.cpp"], [], read_file=make_reader({"a.cpp": "x"})) == []

    def test_finds_basename_reference(self) -> None:
        files = {
            "docs/guide.md": "Refer to helper.hpp for the API",
        }
        result = find_stale_references(
            list(files.keys()),
            ["src/utils/helper.hpp"],
            read_file=make_reader(files),
        )
        assert result == [StaleReference("docs/guide.md", 1, "src/utils/helper.hpp")]

    def test_correct_line_number(self) -> None:
        files = {
            "src/main.cpp": "line1\nline2\n// see helper.hpp\nline4",
        }
        result = find_stale_references(
            list(files.keys()),
            ["src/utils/helper.hpp"],
            read_file=make_reader(files),
        )
        assert result == [StaleReference("src/main.cpp", 3, "src/utils/helper.hpp")]

    def test_multiple_deleted_paths(self) -> None:
        files = {
            "src/main.cpp": "// uses foo.hpp and bar.py",
        }
        result = find_stale_references(
            list(files.keys()),
            ["lib/foo.hpp", "scripts/bar.py"],
            read_file=make_reader(files),
        )
        assert len(result) == 2

    def test_multiple_files_with_references(self) -> None:
        files = {
            "a.cpp": "see helper.hpp",
            "b.py": "no ref here",
            "c.md": "also helper.hpp",
        }
        result = find_stale_references(
            list(files.keys()),
            ["src/helper.hpp"],
            read_file=make_reader(files),
        )
        assert len(result) == 2
        assert {r.file for r in result} == {"a.cpp", "c.md"}


class TestPrintStaleReferences:
    def test_prints_all_references(self, capsys: pytest.CaptureFixture) -> None:
        refs = [
            StaleReference("src/main.cpp", 5, "src/utils/helper.hpp"),
            StaleReference("docs/guide.md", 12, "src/utils/helper.hpp"),
        ]
        print_stale_references(refs)
        output = capsys.readouterr().out
        assert "src/main.cpp:5" in output
        assert "src/utils/helper.hpp" in output
        assert "docs/guide.md:12" in output
