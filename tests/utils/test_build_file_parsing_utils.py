from __future__ import annotations

import pytest

from dev_tools.utils.build_file_parsing_utils import find_rule_calls, rule_has_tag


@pytest.mark.parametrize(
    ("content", "expected_rule_kinds"),
    [
        ('py_venv(name = "venv")', ["py_venv"]),
        ('other_rule(name = "x")', ["other_rule"]),
        (
            """
py_venv(name = "venv")
pkg_tar(name = "archive")
py_venv(
    name = "second",
)
""",
            ["py_venv", "pkg_tar", "py_venv"],
        ),
    ],
)
def test_find_rule_calls_for_content_should_return_rule_kinds(content: str, expected_rule_kinds: list[str]) -> None:
    assert [rule_call.rule_kind for rule_call in find_rule_calls(content)] == expected_rule_kinds


def test_find_rule_calls_for_rule_name_should_filter_rule_calls() -> None:
    content = """
py_venv(name = "venv")
pkg_tar(name = "archive")
"""

    assert [rule_call.rule_kind for rule_call in find_rule_calls(content, "py_venv")] == ["py_venv"]


def test_find_rule_calls_for_nested_parentheses_should_return_full_rule_body() -> None:
    content = """
py_venv(
    name = name + "_venv",
    deps = [":{}_foo".format(name)],
    package_collisions = "ignore",
    tags = ["manual"],
)
"""

    rule_call = next(find_rule_calls(content, "py_venv"))

    assert '":{}_foo".format(name)' in rule_call.body
    assert 'tags = ["manual"]' in rule_call.body


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
