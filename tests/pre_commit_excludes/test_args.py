import argparse
from pathlib import Path

import pytest
from pre_commit_excludes.args import SkippedExclude, parse_skipped_exclude


def test_parse_skipped_exclude_should_return_skipped_exclude() -> None:
    assert parse_skipped_exclude("ruff:packages/example/foo.py") == SkippedExclude(
        hook_id="ruff",
        path=Path("packages/example/foo.py"),
    )


def test_parse_skipped_exclude_for_path_with_colon_should_preserve_colon() -> None:
    assert parse_skipped_exclude("ruff:packages/example:generated/foo.py") == SkippedExclude(
        hook_id="ruff",
        path=Path("packages/example:generated/foo.py"),
    )


def test_parse_skipped_exclude_for_missing_separator_should_raise_error() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="expected HOOK_ID:EXCLUDE_PATH"):
        parse_skipped_exclude("ruff")


@pytest.mark.parametrize("value", [":packages/example/foo.py", "ruff:"])
def test_parse_skipped_exclude_for_empty_value_should_raise_error(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="hook ID and exclude path must not be empty"):
        parse_skipped_exclude(value)
