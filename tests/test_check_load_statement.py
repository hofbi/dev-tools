import pytest

from dev_tools.check_load_statement import has_wrong_load_statement


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("//py:defs.bzl", "py_library")',
        'load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")',
        'load("@aspect_rules_py//py:defs.bzl", _py_library = "py_library")',
        """
load("@rules_python//python:defs.bzl", "py_binary")
load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")
""",
    ],
)
def test_has_wrong_load_statement__rules_python_py_library__should_return_true(load_statement: str) -> None:
    assert has_wrong_load_statement(load_statement, "@rules_python//python:defs.bzl", "py_library") is True


@pytest.mark.parametrize(
    "load_statement",
    [
        'load("@rules_cc//cc:cc_library.bzl", "cc_library")',
        'load("@rules_python//python:defs.bzl", "py_test")',
        'load("@rules_python//python:defs.bzl", "py_binary")',
        'load("@rules_python//python:defs.bzl", _py_binary = "py_binary")',
        'load("@rules_python//python:defs.bzl", "py_binary", "py_test")',
        """
load("@rules_python//python:defs.bzl", "py_binary")
load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")
""",
    ],
)
def test_has_wrong_load_statement__rules_python_py_binary__should_return_false(load_statement: str) -> None:
    assert has_wrong_load_statement(load_statement, "@rules_python//python:defs.bzl", "py_binary") is False
