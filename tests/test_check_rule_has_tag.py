from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dev_tools.check_rule_has_tag import find_invalid_files

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


def test_find_invalid_files_for_rule_without_tag_should_return_file(fs: FakeFilesystem) -> None:
    fs.create_file(
        Path("repo/BUILD.bazel"),
        contents="""
py_venv(
    name = "bad",
)
py_venv(
    name = "good",
    tags = ["manual"],
)
""",
    )

    assert find_invalid_files([Path("repo/BUILD.bazel")], "py_venv", "manual") == [Path("repo/BUILD.bazel")]


def test_find_invalid_files_for_file_without_target_rule_should_return_empty_list(fs: FakeFilesystem) -> None:
    fs.create_file(
        Path("repo/BUILD.bazel"),
        contents="""
pkg_tar(
    name = "archive",
    tags = ["no-remote"],
)
""",
    )

    assert find_invalid_files([Path("repo/BUILD.bazel")], "py_venv", "manual") == []


def test_find_invalid_files_for_rule_with_nested_parentheses_should_return_empty_list(fs: FakeFilesystem) -> None:
    fs.create_file(
        Path("repo/BUILD.bazel"),
        contents="""
py_venv(
    name = name + "_venv",
    deps = [":{}_foo".format(name)],
    package_collisions = "ignore",
    tags = ["manual"],
)
""",
    )

    assert find_invalid_files([Path("repo/BUILD.bazel")], "py_venv", "manual") == []
