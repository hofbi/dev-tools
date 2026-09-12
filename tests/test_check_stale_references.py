from __future__ import annotations

import re
from unittest.mock import patch

from dev_tools.check_stale_references import (
    StaleReference,
    build_path_pattern,
    find_stale_references,
    is_reportable,
)


def nested_pattern(deleted_path: str = "src/lib/foo.hpp") -> str:
    pattern = build_path_pattern(deleted_path, basename_is_unique=True)
    assert pattern is not None
    return pattern


def test_matches_full_path() -> None:
    assert re.search(nested_pattern(), "see src/lib/foo.hpp for details")


def test_matches_full_path_with_leading_slash() -> None:
    assert re.search(nested_pattern(), "see /src/lib/foo.hpp for details")


def test_matches_full_path_with_dotdot() -> None:
    assert re.search(nested_pattern(), "see ../src/lib/foo.hpp for details")


def test_matches_unique_basename() -> None:
    assert re.search(nested_pattern(), "see foo.hpp for details")


def test_matches_unique_basename_with_dotdot() -> None:
    assert re.search(nested_pattern(), "see ../../foo.hpp for details")


def test_does_not_match_intermediate_suffix() -> None:
    # The parallel-subtree case: another module has the same modules/main/main.tf layout.
    pattern = build_path_pattern("event-hub/modules/main/main.tf", basename_is_unique=False)
    assert pattern is not None
    assert not re.search(pattern, "see [main.tf](./modules/main/main.tf) here")
    assert re.search(pattern, "see event-hub/modules/main/main.tf here")


def test_no_substring_match() -> None:
    assert not re.search(nested_pattern(), "notfoo.hpp")


def test_no_match_with_dot_suffix() -> None:
    assert not re.search(nested_pattern(), "foo.hpp.bak")


def test_no_match_with_dash_suffix() -> None:
    assert not re.search(nested_pattern(), "foo.hpp-old")


def test_dot_in_extension_is_literal() -> None:
    assert not re.search(nested_pattern(), "fooXhpp")


def test_shared_basename_is_not_matched_alone() -> None:
    pattern = build_path_pattern("src/lib/foo.hpp", basename_is_unique=False)
    assert pattern is not None
    assert not re.search(pattern, "see foo.hpp for details")
    assert re.search(pattern, "see src/lib/foo.hpp for details")


def test_root_level_path_with_shared_basename_has_no_pattern() -> None:
    assert build_path_pattern("CMakeLists.txt", basename_is_unique=False) is None


def test_root_level_path_without_extension_has_no_pattern() -> None:
    assert build_path_pattern("CONTRIBUTORS", basename_is_unique=True) is None


def test_root_level_path_with_unique_extension_is_matched() -> None:
    pattern = build_path_pattern("ChangeLog.md", basename_is_unique=True)
    assert pattern is not None
    assert re.search(pattern, "run make ChangeLog.md")


def test_reports_markdown_link() -> None:
    assert is_reportable("docs/guide.md", "see [the guide](../src/lib/foo.hpp)")


def test_skips_c_include() -> None:
    assert not is_reportable("src/main.cpp", '#include "src/lib/foo.hpp"')


def test_skips_python_import() -> None:
    assert not is_reportable("tool.py", "from pkg.helper import thing")


def test_skips_bazel_load() -> None:
    assert not is_reportable("BUILD.bazel", 'load("//src:defs.bzl", "thing")')


def test_skips_build_file_source_list() -> None:
    assert not is_reportable("BUILD", '    srcs = ["foo.cpp"],')


def test_skips_makefile_variants() -> None:
    assert not is_reportable("lib/Makefile.inc", "  uint-bset.h        \\")
    assert not is_reportable("src/Makefile.am", "noinst_HEADERS += src/group_impl.h")


def test_skips_continued_javascript_import() -> None:
    assert not is_reportable("lib/adapters/http.js", "} from '../helpers/progressEventReducer.js';")


def test_nolint_marker_skips_line() -> None:
    assert not is_reportable("docs/server.rst", "$ python hello.py  .. nolint(stale_references)")


def test_nolint_marker_works_in_any_comment_syntax() -> None:
    assert not is_reportable("docs/guide.md", "run setup.py <!-- nolint(stale_references) -->")
    assert not is_reportable("src/config.py", 'from_file("config.toml")  # nolint(stale_references)')


def test_reports_comment_inside_build_file() -> None:
    assert is_reportable("CMakeLists.txt", "# see docs/design.md for rationale")


def test_skips_changelog() -> None:
    assert not is_reportable("ChangeLog.md", "- Moved helpers to fmt/xchar.h")


def test_skips_release_notes() -> None:
    assert not is_reportable("doc/release-notes.md", "renamed foo.hpp to bar.hpp")


def test_stale_reference_str() -> None:
    ref = StaleReference("src/main.cpp", 5, "src/utils/helper.hpp")
    assert str(ref) == "src/main.cpp:5 references src/utils/helper.hpp"


def find_with(deleted: set[str], tracked: list[str], grep: list[tuple[str, int, str]]) -> list[StaleReference]:
    with (
        patch("dev_tools.check_stale_references.get_deleted_paths", return_value=deleted),
        patch("dev_tools.check_stale_references.get_tracked_paths", return_value=tracked),
        patch("dev_tools.check_stale_references.git_grep", return_value=grep),
    ):
        return find_stale_references()


def test_finds_reference_to_deleted_file() -> None:
    result = find_with(
        {"src/utils/helper.hpp"},
        ["src/main.cpp"],
        [("src/main.cpp", 1, "// see src/utils/helper.hpp for details")],
    )
    assert result == [StaleReference("src/main.cpp", 1, "src/utils/helper.hpp")]


def test_no_reference_no_finding() -> None:
    assert find_with({"src/utils/helper.hpp"}, ["src/main.cpp"], []) == []


def test_empty_deleted_paths_returns_empty() -> None:
    assert find_with(set(), ["src/main.cpp"], []) == []


def test_skips_deleted_file_itself() -> None:
    result = find_with(
        {"src/utils/helper.hpp"},
        ["src/utils/helper.hpp"],
        [("src/utils/helper.hpp", 1, "helper.hpp title")],
    )
    assert result == []


def test_reports_each_referencing_file_once() -> None:
    result = find_with(
        {"src/utils/helper.hpp"},
        ["docs/guide.md"],
        [("docs/guide.md", 3, "see helper.hpp"), ("docs/guide.md", 9, "and helper.hpp again")],
    )
    assert result == [StaleReference("docs/guide.md", 3, "src/utils/helper.hpp")]


def test_skips_tool_checked_reference() -> None:
    result = find_with(
        {"src/utils/helper.hpp"},
        ["src/main.cpp"],
        [("src/main.cpp", 1, '#include "src/utils/helper.hpp"')],
    )
    assert result == []


def test_nolint_marker_suppresses_finding() -> None:
    result = find_with(
        {"src/utils/helper.hpp"},
        ["docs/guide.md"],
        [("docs/guide.md", 3, "create helper.hpp yourself <!-- nolint(stale_references) -->")],
    )
    assert result == []


def test_deletion_without_specific_enough_pattern_is_skipped() -> None:
    result = find_with(
        {"CONTRIBUTORS"},
        ["src/main.cpp"],
        [("src/main.cpp", 1, "// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS")],
    )
    assert result == []
