# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pre_commit_excludes.hook_utils import (
    Hook,
)

from dev_tools.check_useless_exclude_paths_hooks import have_non_existent_paths_or_duplicates

if TYPE_CHECKING:
    import pytest
    from pyfakefs.fake_filesystem import FakeFilesystem


def test_have_non_existent_paths_or_duplicates_for_non_existing_paths(
    capsys: pytest.CaptureFixture,
    fs: FakeFilesystem,
) -> None:
    fs.create_file(Path("Repo/existing_path"))
    assert have_non_existent_paths_or_duplicates(
        [
            Hook(
                "test_id",
                [Path("Repo/existing_path"), Path("Repo/non_existing_path1"), Path("Repo/non_existing_path2")],
            ),
        ],
    )
    output = capsys.readouterr().out
    assert "test_id" in output
    assert "non-existing" in output
    assert "non_existing_path1" in output
    assert "non_existing_path2" in output


def test_have_non_existent_paths_or_duplicates_for_duplicate_paths(
    capsys: pytest.CaptureFixture,
    fs: FakeFilesystem,
) -> None:
    fs.create_file(Path("Repo/existing_path1"))
    fs.create_file(Path("Repo/existing_path2"))
    assert have_non_existent_paths_or_duplicates(
        [
            Hook(
                "test_id",
                [
                    Path("Repo/existing_path1"),
                    Path("Repo/existing_path2"),
                    Path("Repo/existing_path1"),
                    Path("Repo/existing_path2"),
                ],
            ),
        ],
    )
    output = capsys.readouterr().out
    assert "test_id" in output
    assert "duplicates" in output
    assert "existing_path1" in output
    assert "existing_path2" in output
