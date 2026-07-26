# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dev_tools.check_repo_links import (
    BrokenLink,
    build_set_of_valid_link_targets,
    build_target_existence_check,
    find_broken_links,
    find_broken_links_in_content,
    main,
    offset_to_line_and_column,
    print_broken_links,
    resolve_link_target,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem

TRACKED = ["README.md", "docs/readme.md", "src/foo.hpp", "src/util/helper.h", "src/c.h"]


def scan(text: str, file_path: str = "src/foo.cpp", *, tracked: tuple[str, ...] = ()) -> list[BrokenLink]:
    return find_broken_links_in_content(text.encode(), file_path, build_target_existence_check(tracked))


# --- resolve_link_target --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("link", "file_path", "expected"),
    [
        ("foo.hpp", "src/foo.cpp", "src/foo.hpp"),
        ("../c.h", "src/util/helper.h", "src/c.h"),
        ("/src/foo.hpp", "docs/readme.md", "src/foo.hpp"),
        ("readme.md", "README.md", "readme.md"),
        ("foo.hpp#section", "src/foo.cpp", "src/foo.hpp"),
        ("foo.hpp?v=1", "src/foo.cpp", "src/foo.hpp"),
        ("foo.hpp.", "src/foo.cpp", "src/foo.hpp"),
    ],
    ids=[
        "sibling file",
        "parent traversal",
        "leading slash is repo root",
        "file at repo root",
        "anchor stripped",
        "query stripped",
        "trailing punctuation stripped",
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


@pytest.mark.parametrize(
    ("text", "tracked"),
    [
        pytest.param("// see @repo foo.hpp for details", ("src/foo.hpp",), id="valid link"),
        pytest.param(" * @report_new: populate the report", (), id="doxygen @report tag"),
        pytest.param('import { Button } from "@repo/ui";', (), id="npm @repo scope"),
        pytest.param("foo@repo missing.md", (), id="marker preceded by word char"),
        pytest.param("// @repo https://example.com/page", (), id="url target"),
    ],
)
def test_scan_reports_no_broken_links(text: str, tracked: tuple[str, ...]) -> None:
    assert scan(text, tracked=tracked) == []


def test_leading_slash_resolves_from_repo_root() -> None:
    assert scan("// @repo /src/foo.hpp", file_path="docs/readme.md", tracked=("src/foo.hpp",)) == []
    assert [b.link for b in scan("// @repo /src/nope.hpp", file_path="docs/readme.md")] == ["/src/nope.hpp"]


def test_multiple_findings_with_correct_lines_and_columns() -> None:
    broken = scan(
        "// @repo foo.hpp\n// @repo missing1.md\ncode();\n/* @repo missing2.md */\n", tracked=("src/foo.hpp",)
    )
    assert [(b.line, b.column, b.link) for b in broken] == [(2, 10, "missing1.md"), (4, 10, "missing2.md")]


# --- find_broken_links (file system) --------------------------------------------------------


def test_find_broken_links_reads_files(fs: FakeFilesystem) -> None:
    fs.create_file(Path("src/a.cpp"), contents="// @repo missing.h\n")
    fs.create_file(Path("src/b.cpp"), contents="// @repo a.cpp\n")
    broken = find_broken_links(
        [Path("src/a.cpp"), Path("src/b.cpp")], Path.cwd(), build_target_existence_check(["src/a.cpp"])
    )
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
    monkeypatch.setattr("dev_tools.check_repo_links.get_repository_root", Path.cwd)
    monkeypatch.setattr("dev_tools.check_repo_links.list_tracked_files", lambda _root: ["src/a.cpp"])
    assert main(["src/a.cpp"]) == 1
    assert "src/a.cpp:1:10 missing.h" in capsys.readouterr().out


def test_main_returns_zero_for_valid_links(fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch) -> None:
    fs.create_file(Path("src/a.cpp"), contents="// @repo b.h\n")
    fs.create_file(Path("src/b.h"), contents="")
    monkeypatch.setattr("dev_tools.check_repo_links.get_repository_root", Path.cwd)
    monkeypatch.setattr("dev_tools.check_repo_links.list_tracked_files", lambda _root: ["src/a.cpp", "src/b.h"])
    assert main(["src/a.cpp"]) == 0
