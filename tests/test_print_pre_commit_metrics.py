from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from dev_tools.check_useless_exclude_paths_hooks import Hook
from dev_tools.print_pre_commit_metrics import create_excluded_files_report, write_pre_commit_metrics

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


def test_create_excluded_files_report__hook_without_excluded_files__should_be_all_zero() -> None:
    hook = Hook("test-hook", [])

    result = create_excluded_files_report([hook])

    assert result == {"total_excluded_files": 0, "hooks": []}


def test_create_excluded_files_report__hook_with_excludes__should_be_two(fs: FakeFilesystem) -> None:
    fs.create_file("file1.txt")
    fs.create_dir("dir1")
    fs.create_file("dir1/file2.txt")
    hook = Hook("test-hook", [Path("file1.txt"), Path("dir1/")])

    result = create_excluded_files_report([hook])

    assert result == {"total_excluded_files": 2, "hooks": [{"hook_id": "test-hook", "excluded_files_count": 2}]}


def test_create_excluded_files_report__two_hooks_with_excludes__should_be_three_in_total(fs: FakeFilesystem) -> None:
    fs.create_file("file1.txt")
    fs.create_dir("dir1")
    fs.create_file("dir1/file2.txt")
    hook1 = Hook("test-hook-1", [Path("file1.txt")])
    hook2 = Hook("test-hook-2", [Path("file1.txt"), Path("dir1/")])

    result = create_excluded_files_report([hook1, hook2])

    assert result == {
        "total_excluded_files": 3,
        "hooks": [
            {"hook_id": "test-hook-1", "excluded_files_count": 1},
            {"hook_id": "test-hook-2", "excluded_files_count": 2},
        ],
    }


def test_write_pre_commit_metrics__should_create_file_with_json_data(fs: FakeFilesystem) -> None:  # noqa: ARG001
    output_data = {"total_excluded_files": 5, "hooks": [{"hook_id": "test-hook", "excluded_files_count": 5}]}
    output_file = Path("output/metrics.json")

    write_pre_commit_metrics(output_data, output_file)

    assert output_file.exists()
    assert json.loads(output_file.read_text()) == output_data
