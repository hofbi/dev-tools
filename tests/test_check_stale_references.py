from __future__ import annotations

import re
from unittest.mock import patch

from dev_tools.check_stale_references import (
    StaleReference,
    build_path_pattern,
    find_stale_references,
)


def test_matches_full_path() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert re.search(pattern, "see src/lib/foo.hpp for details")


def test_matches_full_path_with_leading_slash() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert re.search(pattern, "see /src/lib/foo.hpp for details")


def test_matches_intermediate_suffix() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert re.search(pattern, "see lib/foo.hpp here")


def test_matches_intermediate_suffix_with_dotdot() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert re.search(pattern, "see ../lib/foo.hpp here")


def test_matches_basename() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert re.search(pattern, "see foo.hpp for details")


def test_matches_basename_with_dotdot() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert re.search(pattern, "see ../../foo.hpp for details")


def test_no_substring_match() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert not re.search(pattern, "notfoo.hpp")


def test_no_match_with_dot_suffix() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert not re.search(pattern, "foo.hpp.bak")


def test_no_match_with_dash_suffix() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert not re.search(pattern, "foo.hpp-old")


def test_dot_in_extension_is_literal() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp")
    assert not re.search(pattern, "fooXhpp")


def test_stale_reference_str() -> None:
    ref = StaleReference("src/main.cpp", 5, "src/utils/helper.hpp")
    assert str(ref) == "src/main.cpp:5 references src/utils/helper.hpp"


@patch("dev_tools.check_stale_references.git_grep")
@patch("dev_tools.check_stale_references.get_deleted_paths")
def test_finds_reference_to_deleted_file(mock_deleted, mock_grep) -> None:
    mock_deleted.return_value = {"src/utils/helper.hpp"}
    mock_grep.return_value = [("src/main.cpp", 1)]
    result = find_stale_references()
    assert result == [StaleReference("src/main.cpp", 1, "src/utils/helper.hpp")]


@patch("dev_tools.check_stale_references.git_grep")
@patch("dev_tools.check_stale_references.get_deleted_paths")
def test_no_reference_no_finding(mock_deleted, mock_grep) -> None:
    mock_deleted.return_value = {"src/utils/helper.hpp"}
    mock_grep.return_value = []
    result = find_stale_references()
    assert result == []


@patch("dev_tools.check_stale_references.git_grep")
@patch("dev_tools.check_stale_references.get_deleted_paths")
def test_skips_deleted_file_itself(mock_deleted, mock_grep) -> None:
    mock_deleted.return_value = {"src/utils/helper.hpp"}
    mock_grep.return_value = [("src/utils/helper.hpp", 1)]
    result = find_stale_references()
    assert result == []


@patch("dev_tools.check_stale_references.get_deleted_paths")
def test_empty_deleted_paths_returns_empty(mock_deleted) -> None:
    mock_deleted.return_value = set()
    assert find_stale_references() == []


@patch("dev_tools.check_stale_references.git_grep")
@patch("dev_tools.check_stale_references.get_deleted_paths")
def test_multiple_files_with_references(mock_deleted, mock_grep) -> None:
    mock_deleted.return_value = {"src/helper.hpp"}
    mock_grep.return_value = [
        ("a.cpp", 1),
        ("c.md", 3),
    ]
    result = find_stale_references()
    assert len(result) == 2
    assert {r.from_file for r in result} == {"a.cpp", "c.md"}
