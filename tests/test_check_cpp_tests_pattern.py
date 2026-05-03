import re

import pytest

from dev_tools.pre_commit_utils import get_hook_by_id


@pytest.fixture
def cpp_tests_name_hook() -> dict:
    return get_hook_by_id("check-cpp-and-cu-unit-test-naming-pattern")


def test__hook_validating_test_filenames__is_defined_for_files(cpp_tests_name_hook: dict) -> None:
    assert "files" in cpp_tests_name_hook


@pytest.mark.parametrize(
    "filename",
    [
        "src/tests/foo_test.cpp",
        "src/tests/foo_test.cu",
        "src/tests/local/foo_test.cpp",
        "src/tests/pythontest.py",
        "src/tests/footest.cpp.txt",
        "src/python_tests/foo.py",
        "src/python_test/foo.py",
    ],
)
def test__hook_validating_test_filenames__allows_valid_cases(cpp_tests_name_hook: dict, filename: str) -> None:
    deny_files_pattern: str = cpp_tests_name_hook["files"]
    assert not re.match(deny_files_pattern, filename), "Valid test filename should not match the deny pattern"


@pytest.mark.parametrize(
    "filename", ["src/tests/footest.cpp", "src/tests/foo_tests.cpp", "src/test/foo_test.cpp", "src/foo_test.cu"]
)
def test__hook_validating_test_filenames__denies_invalid_cases(cpp_tests_name_hook: dict, filename: str) -> None:
    deny_files_pattern: str = cpp_tests_name_hook["files"]
    assert re.match(deny_files_pattern, filename), "Invalid test filename should match the deny pattern"
