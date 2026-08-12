# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

import re
from unittest.mock import patch

from dev_tools.check_stale_references import (
    StaleReference,
    build_path_pattern,
    find_stale_references,
)


class TestBuildPathPattern:
    def test_matches_full_path(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert re.search(pattern, "see src/lib/foo.hpp for details")

    def test_matches_full_path_with_leading_slash(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert re.search(pattern, "see /src/lib/foo.hpp for details")

    def test_matches_intermediate_suffix(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert re.search(pattern, "see lib/foo.hpp here")

    def test_matches_intermediate_suffix_with_dotdot(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert re.search(pattern, "see ../lib/foo.hpp here")

    def test_matches_basename(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert re.search(pattern, "see foo.hpp for details")

    def test_matches_basename_with_dotdot(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert re.search(pattern, "see ../../foo.hpp for details")

    def test_no_substring_match(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert not re.search(pattern, "notfoo.hpp")

    def test_no_match_with_dot_suffix(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert not re.search(pattern, "foo.hpp.bak")

    def test_no_match_with_dash_suffix(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert not re.search(pattern, "foo.hpp-old")

    def test_dot_in_extension_is_literal(self) -> None:
        pattern = build_path_pattern("src/lib/foo.hpp")
        assert not re.search(pattern, "fooXhpp")


class TestStaleReferenceStr:
    def test_str(self) -> None:
        ref = StaleReference("src/main.cpp", 5, "src/utils/helper.hpp")
        assert str(ref) == "src/main.cpp:5 references src/utils/helper.hpp"


class TestFindStaleReferences:
    @patch("dev_tools.check_stale_references.git_grep")
    def test_finds_reference_to_deleted_file(self, mock_grep) -> None:
        mock_grep.return_value = [("src/main.cpp", 1, "// see src/utils/helper.hpp for details")]
        result = find_stale_references(["src/utils/helper.hpp"])
        assert result == [StaleReference("src/main.cpp", 1, "src/utils/helper.hpp")]

    @patch("dev_tools.check_stale_references.git_grep")
    def test_no_reference_no_finding(self, mock_grep) -> None:
        mock_grep.return_value = []
        result = find_stale_references(["src/utils/helper.hpp"])
        assert result == []

    @patch("dev_tools.check_stale_references.git_grep")
    def test_skips_deleted_file_itself(self, mock_grep) -> None:
        mock_grep.return_value = [("src/utils/helper.hpp", 1, "#include helper.hpp")]
        result = find_stale_references(["src/utils/helper.hpp"])
        assert result == []

    def test_empty_deleted_paths_returns_empty(self) -> None:
        assert find_stale_references([]) == []

    @patch("dev_tools.check_stale_references.git_grep")
    def test_multiple_files_with_references(self, mock_grep) -> None:
        mock_grep.return_value = [
            ("a.cpp", 1, "see helper.hpp"),
            ("c.md", 3, "also helper.hpp"),
        ]
        result = find_stale_references(["src/helper.hpp"])
        assert len(result) == 2
        assert {r.file for r in result} == {"a.cpp", "c.md"}
