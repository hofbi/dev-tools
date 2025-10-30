import re

import pytest

from dev_tools.pre_commit_utils import get_hooks_manifest


def _get_hook_by_id(hook_id: str) -> dict:
    for hook in get_hooks_manifest():
        if hook["id"] == hook_id:
            return hook
    msg = f"{hook_id} not found in hooks manifest"
    raise ValueError(msg)


@pytest.fixture
def rules_python_py_library_hook_name() -> dict:
    return _get_hook_by_id("check-rules-python-py-library")


@pytest.fixture
def rules_python_py_test_hook_name() -> dict:
    return _get_hook_by_id("check-rules-python-py-test")


@pytest.fixture
def rules_python_py_binary_hook_name() -> dict:
    return _get_hook_by_id("check-rules-python-py-binary")


def test__hook_rules_python_py_library__is_defined_for_pygrep_entry(rules_python_py_library_hook_name: dict) -> None:
    assert "entry" in rules_python_py_library_hook_name


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("@rules_python//python:defs.bzl", "py_library")',
        'load("@rules_python//python:defs.bzl", "py_binary", "py_library")',
        'load("@rules_python//python:defs.bzl", "py_library", "py_test")',
    ],
)
def test__hook_rules_python_py_library__should_detect_rules_python_loads(
    rules_python_py_library_hook_name: dict, load_statement: str
) -> None:
    pattern: str = rules_python_py_library_hook_name["entry"]
    assert re.match(pattern, load_statement)


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("@aspect_rules_py//py:defs.bzl", "py_library")',
        'load("//py:defs.bzl", "py_library")',
        'load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")',
        'load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")',
        'load("@rules_python//python:defs.bzl", "py_binary"',
    ],
)
def test__hook_rules_python_py_library__should_not_fail_for_valid_loads(
    rules_python_py_library_hook_name: dict, load_statement: str
) -> None:
    pattern: str = rules_python_py_library_hook_name["entry"]
    assert not re.match(pattern, load_statement)


def test__hook_rules_python_py_test__is_defined_for_pygrep_entry(
    rules_python_py_test_hook_name: dict,
) -> None:
    assert "entry" in rules_python_py_test_hook_name


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("@rules_python//python:defs.bzl", "py_test")',
        'load("@rules_python//python:defs.bzl", "py_binary", "py_test")',
        'load("@rules_python//python:defs.bzl", "py_library", "py_test")',
    ],
)
def test__hook_rules_python_py_test__should_detect_rules_python_loads(
    rules_python_py_test_hook_name: dict, load_statement: str
) -> None:
    pattern: str = rules_python_py_test_hook_name["entry"]
    assert re.match(pattern, load_statement)


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("@aspect_rules_py//py:defs.bzl", "py_test")',
        'load("//py:defs.bzl", "py_test")',
        'load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_test")',
        'load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")',
        'load("@rules_python//python:defs.bzl", "py_binary"',
    ],
)
def test__hook_rules_python_py_test__should_not_fail_for_valid_loads(
    rules_python_py_test_hook_name: dict, load_statement: str
) -> None:
    pattern: str = rules_python_py_test_hook_name["entry"]
    assert not re.match(pattern, load_statement)


def test__hook_rules_python_py_binary__is_defined_for_pygrep_entry(
    rules_python_py_binary_hook_name: dict,
) -> None:
    assert "entry" in rules_python_py_binary_hook_name


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("@rules_python//python:defs.bzl", "py_binary")',
        'load("@rules_python//python:defs.bzl", "py_binary", "py_library")',
        'load("@rules_python//python:defs.bzl", "py_binary", "py_test")',
    ],
)
def test__hook_rules_python_py_binary__should_detect_rules_python_loads(
    rules_python_py_binary_hook_name: dict, load_statement: str
) -> None:
    pattern: str = rules_python_py_binary_hook_name["entry"]
    assert re.match(pattern, load_statement)


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("@aspect_rules_py//py:defs.bzl", "py_binary")',
        'load("//py:defs.bzl", "py_binary")',
        'load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")',
        'load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_test")',
        'load("@rules_python//python:defs.bzl", "py_library"',
    ],
)
def test__hook_rules_python_py_binary__should_not_fail_for_valid_loads(
    rules_python_py_binary_hook_name: dict, load_statement: str
) -> None:
    pattern: str = rules_python_py_binary_hook_name["entry"]
    assert not re.match(pattern, load_statement)
