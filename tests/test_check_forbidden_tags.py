from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from dev_tools.check_forbidden_tags import find_files_with_forbidden_tags, main

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


def test_find_files_with_forbidden_tags_for_forbidden_tag_should_return_file(fs: FakeFilesystem) -> None:
    fs.create_file(
        Path("repo/BUILD.bazel"),
        contents="""
py_venv(
    name = "bad",
    tags = ["no-remote"],
)
""",
    )

    assert find_files_with_forbidden_tags([Path("repo/BUILD.bazel")], "no-remote", None) == [Path("repo/BUILD.bazel")]


def test_find_files_with_forbidden_tags_for_allowed_rule_kind_should_return_empty_list(fs: FakeFilesystem) -> None:
    fs.create_file(
        Path("repo/BUILD.bazel"),
        contents="""
pkg_tar(
    name = "archive",
    tags = ["no-remote"],
)
""",
    )

    assert find_files_with_forbidden_tags([Path("repo/BUILD.bazel")], "no-remote", re.compile("pkg_tar")) == []


def test_main_for_violation_should_return_one(fs: FakeFilesystem, capsys) -> None:
    fs.create_file(
        Path("repo/BUILD.bazel"),
        contents="""
py_venv(
    name = "bad",
    tags = ["no-remote"],
)
""",
    )

    assert main(["--forbidden-tag=no-remote", "repo/BUILD.bazel"]) == 1
    assert "contains a rule with `tags` containing `no-remote`" in capsys.readouterr().out
