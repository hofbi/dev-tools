import re

import pytest

from dev_tools.pre_commit_utils import get_hook_by_id


@pytest.fixture
def readme_md_consistency_hook() -> dict:
    return get_hook_by_id("check-readme-md-consistency")


def test__hook_validating_readme_filenames__is_defined_for_files(readme_md_consistency_hook: dict) -> None:
    assert "files" in readme_md_consistency_hook


@pytest.mark.parametrize(
    "filename",
    [
        "README.md",
        "some/path/README.md",
        "packages/foo/README.md",
        "NOT_README.md",
        "README.md.backup/file.py",
        "docs/readme_notes.md",
        "readme/something.md",
    ],
)
def test__hook_validating_readme_filenames__allows_valid_cases(readme_md_consistency_hook: dict, filename: str) -> None:
    deny_files_pattern: str = readme_md_consistency_hook["files"]
    assert not re.search(deny_files_pattern, filename), "Valid README filename should not match the deny pattern"


@pytest.mark.parametrize(
    "filename",
    [
        "README",
        "README.txt",
        "README.MD",
        "Readme.md",
        "readme.md",
        "readme",
        "readme.txt",
        "some/path/README",
        "some/path/README.txt",
        "some/path/README.MD",
        "some/path/Readme.md",
        "some/path/readme.md",
        "packages/foo/readme",
    ],
)
def test__hook_validating_readme_filenames__denies_invalid_cases(
    readme_md_consistency_hook: dict, filename: str
) -> None:
    deny_files_pattern: str = readme_md_consistency_hook["files"]
    pattern_matches = re.search(deny_files_pattern, filename)
    assert pattern_matches, f"Invalid README filename '{filename}' should match the deny pattern '{deny_files_pattern}'"
