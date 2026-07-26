# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dev_tools.check_repo_links import (
    BrokenLink,
    build_set_of_valid_link_targets,
    find_broken_links,
    find_broken_links_in_content,
    main,
    offset_to_line_and_column,
    print_broken_links,
    resolve_link_target,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyfakefs.fake_filesystem import FakeFilesystem

TRACKED = ["README.md", "docs/readme.md", "src/foo.hpp", "src/util/helper.h", "src/c.h"]


def exists(*paths: str) -> Callable[[str], bool]:
    return build_set_of_valid_link_targets(paths).__contains__


def scan(text: str, file_path: str = "src/foo.cpp", *, tracked: tuple[str, ...] = ()) -> list[BrokenLink]:
    return find_broken_links_in_content(text.encode(), file_path, exists(*tracked))


# --- resolve_link_target --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("link", "file_path", "expected"),
    [
        ("foo.hpp", "src/foo.cpp", "src/foo.hpp"),  # sibling file
        ("../c.h", "src/util/helper.h", "src/c.h"),  # parent traversal
        ("/src/foo.hpp", "docs/readme.md", "src/foo.hpp"),  # leading slash = repo root
        ("readme.md", "README.md", "readme.md"),  # file at the repo root
        ("foo.hpp#section", "src/foo.cpp", "src/foo.hpp"),  # anchor stripped
        ("foo.hpp?v=1", "src/foo.cpp", "src/foo.hpp"),  # query stripped
        ("foo.hpp.", "src/foo.cpp", "src/foo.hpp"),  # trailing prose punctuation stripped
    ],
)
def test_resolve_link_target(link: str, file_path: str, expected: str) -> None:
    assert resolve_link_target(link, file_path) == expected


@pytest.mark.parametrize("link", ["https://example.com/x", "http://example.com", "mailto:a@b.com", "#anchor", ""])
def test_resolve_link_target_skips_non_relative_links(link: str) -> None:
    assert resolve_link_target(link, "src/foo.cpp") is None


# --- offset_to_line_and_column --------------------------------------------------------------


def test_offset_to_line_and_column() -> None:
    content = b"line1\nline2\nXhere"
    assert offset_to_line_and_column(content, 0) == (1, 1)
    assert offset_to_line_and_column(content, 12) == (3, 1)  # 'X' after two newlines


# --- build_valid_target_set -----------------------------------------------------------------


def test_build_valid_target_set_includes_files_dirs_and_root() -> None:
    valid = build_set_of_valid_link_targets(["src/util/helper.h", "README.md"])
    assert valid.issuperset({"src/util/helper.h", "src/util", "src", "README.md", "."})
    assert "src/missing.h" not in valid


# --- find_broken_links_in_content -----------------------------------------------------------


def test_broken_link_is_reported_with_location() -> None:
    assert scan("// see @repo missing/file.md here") == [BrokenLink("src/foo.cpp", 1, 14, "missing/file.md")]


def test_valid_link_is_not_reported() -> None:
    assert scan("// see @repo foo.hpp for details", tracked=("src/foo.hpp",)) == []


def test_doxygen_param_tag_is_ignored() -> None:
    # `@report...` has no whitespace after `@repo`, so the marker never matches.
    assert scan(" * @report_new: populate the report\n * @reported: bool") == []


def test_npm_scope_is_ignored() -> None:
    # `@repo/ui` is followed by `/`, not whitespace, so it is not our marker.
    assert scan('import { Button } from "@repo/ui";') == []


def test_marker_must_not_follow_word_character() -> None:
    assert scan("foo@repo missing.md") == []


def test_url_target_is_skipped() -> None:
    assert scan("// @repo https://example.com/page") == []


def test_leading_slash_resolves_from_repo_root() -> None:
    assert scan("// @repo /src/foo.hpp", file_path="docs/readme.md", tracked=("src/foo.hpp",)) == []
    assert [b.link for b in scan("// @repo /src/nope.hpp", file_path="docs/readme.md")] == ["/src/nope.hpp"]


def test_multiple_findings_with_correct_lines_and_columns() -> None:
    broken = scan(
        "// @repo foo.hpp\n// @repo missing1.md\ncode();\n/* @repo missing2.md */\n", tracked=("src/foo.hpp",)
    )
    assert [(b.line, b.column, b.link) for b in broken] == [(2, 10, "missing1.md"), (4, 10, "missing2.md")]


def test_prefilter_skips_files_without_marker() -> None:
    assert scan("int main() { return 0; }") == []


# --- find_broken_links (file system) --------------------------------------------------------


def test_find_broken_links_reads_files(fs: FakeFilesystem) -> None:
    fs.create_file(Path("src/a.cpp"), contents="// @repo missing.h\n")
    fs.create_file(Path("src/b.cpp"), contents="// @repo a.cpp\n")
    broken = find_broken_links([Path("src/a.cpp"), Path("src/b.cpp")], exists("src/a.cpp"))
    assert broken == [BrokenLink("src/a.cpp", 1, 10, "missing.h")]


# --- report_broken_links --------------------------------------------------------------------


def test_print_broken_links_prints_findings(capsys: pytest.CaptureFixture) -> None:
    print_broken_links([BrokenLink("src/a.cpp", 3, 12, "missing.h")])
    out = capsys.readouterr().out
    assert "Found broken links:" in out
    assert "src/a.cpp:3:12 missing.h" in out


def test_print_broken_links_is_silent_when_empty(capsys: pytest.CaptureFixture) -> None:
    print_broken_links([])
    assert not capsys.readouterr().out


# --- main -----------------------------------------------------------------------------------


def test_main_returns_one_for_broken_links(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    fs.create_file(Path("src/a.cpp"), contents="// @repo missing.h\n")
    monkeypatch.setattr("dev_tools.check_repo_links.list_tracked_files", lambda: ["src/a.cpp"])
    assert main(["src/a.cpp"]) == 1
    assert "src/a.cpp:1:10 missing.h" in capsys.readouterr().out


def test_main_returns_zero_for_valid_links(fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch) -> None:
    fs.create_file(Path("src/a.cpp"), contents="// @repo b.h\n")
    fs.create_file(Path("src/b.h"), contents="")
    monkeypatch.setattr("dev_tools.check_repo_links.list_tracked_files", lambda: ["src/a.cpp", "src/b.h"])
    assert main(["src/a.cpp"]) == 0
