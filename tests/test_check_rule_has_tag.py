from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dev_tools.check_rule_has_tag import find_invalid_files, find_rule_calls, rule_has_tag

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.mark.parametrize(
    ("content", "expected_rule_count"),
    [
        ('py_venv(name = "venv")', 1),
        ('other_rule(name = "x")', 0),
        (
            """
py_venv(name = "venv")
pkg_tar(name = "archive")
py_venv(
    name = "second",
)
""",
            2,
        ),
        (
            """
py_venv(
    name = name + "_venv",
    deps = [":{}_foo".format(name)],
    package_collisions = "ignore",
    tags = ["manual"],
)
""",
            1,
        ),
    ],
)
def test_find_rule_calls_for_content_should_return_expected_rule_count(content: str, expected_rule_count: int) -> None:
    assert len(find_rule_calls(content, "py_venv")) == expected_rule_count


@pytest.mark.parametrize(
    ("rule_body", "tag"),
    [
        ('name = "venv", tags = ["manual"]', "manual"),
        ('name = "venv", tags = ["manual", "no-remote"]', "manual"),
        ('name = "venv", tags = [\n    "manual",\n]', "manual"),
        ('name = "archive", tags = ["no-remote"]', "no-remote"),
    ],
)
def test_rule_has_tag_for_matching_tag_should_return_true(rule_body: str, tag: str) -> None:
    assert rule_has_tag(rule_body, tag) is True


@pytest.mark.parametrize(
    ("rule_body", "tag"),
    [
        ('name = "venv"', "manual"),
        ('name = "venv", tags = ["not-manual"]', "manual"),
        ('name = "venv", tags = []  # manual', "manual"),
        ('name = "archive", tags = ["remote"]', "no-remote"),
        ('name = "thing", package_collisions = "ignore"', "manual"),
    ],
)
def test_rule_has_tag_for_non_matching_tag_should_return_false(rule_body: str, tag: str) -> None:
    assert rule_has_tag(rule_body, tag) is False


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
