from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from pre_commit_excludes.hook_utils import Hook, load_config, write_config
from pre_commit_excludes.remove_unnecessary_excludes import (
    get_files_from_exclude_path,
    get_hooks_to_cleanup,
    run_pre_commit,
    write_tmp_pre_commit_config_without_excludes,
)

if TYPE_CHECKING:
    import pytest
    from pyfakefs.fake_filesystem import FakeFilesystem


def test_get_hooks_to_cleanup_for_selected_hooks_should_return_matching_hooks() -> None:
    check_snake_case_hook = Hook("check-snake-case", [Path("foo.py")])
    buildifier_hook = Hook("buildifier", [Path("BUILD.bazel")])
    hooks = [
        check_snake_case_hook,
        buildifier_hook,
        Hook("ruff", [Path("bar.py")]),
    ]

    assert get_hooks_to_cleanup(hooks, ["buildifier", "check-snake-case"]) == [
        check_snake_case_hook,
        buildifier_hook,
    ]


def test_get_hooks_to_cleanup_for_no_selected_hooks_should_return_empty_list() -> None:
    hooks = [
        Hook("check-snake-case", [Path("foo.py")]),
        Hook("buildifier", [Path("BUILD.bazel")]),
    ]

    assert get_hooks_to_cleanup(hooks, None) == []


def test_get_hooks_to_cleanup_for_unknown_selected_hook_should_return_empty_list() -> None:
    hooks = [
        Hook("check-snake-case", [Path("foo.py")]),
        Hook("buildifier", [Path("BUILD.bazel")]),
    ]

    assert get_hooks_to_cleanup(hooks, ["unknown-hook"]) == []


def test_get_files_from_exclude_path_for_file_should_return_file(fs: FakeFilesystem) -> None:
    exclude_path = Path("Repo/excluded_file.txt")
    fs.create_file(exclude_path)

    assert get_files_from_exclude_path(exclude_path) == [exclude_path]


def test_get_files_from_exclude_path_for_directory_should_return_all_descendants(fs: FakeFilesystem) -> None:
    exclude_path = Path("Repo/excluded_directory")
    fs.create_file(exclude_path / "file1.txt")
    fs.create_file(exclude_path / "subdirectory" / "file2.txt")

    assert set(get_files_from_exclude_path(exclude_path)) == {
        exclude_path / "file1.txt",
        exclude_path / "subdirectory",
        exclude_path / "subdirectory" / "file2.txt",
    }


def test_get_files_from_exclude_path_for_empty_directory_should_return_empty_list(fs: FakeFilesystem) -> None:
    exclude_path = Path("Repo/excluded_directory")
    fs.create_dir(exclude_path)

    assert get_files_from_exclude_path(exclude_path) == []


def test_write_tmp_pre_commit_config_without_excludes_should_remove_all_excludes(fs: FakeFilesystem) -> None:
    config_file = Path("Test_directory/.pre-commit-config.yaml")
    fs.create_dir(config_file.parent)
    config = {
        "repos": [
            {
                "repo": "meta",
                "hooks": [
                    {
                        "id": "check-hooks-apply",
                        "exclude": "foo",
                    },
                ],
            },
            {
                "repo": "local",
                "hooks": [
                    {
                        "id": "check-snake-case",
                        "name": "check snake case",
                        "entry": "python3 foo.py",
                        "language": "python",
                        "exclude": "packages/thirdparty/",
                    },
                    {
                        "id": "ruff",
                        "name": "ruff",
                        "entry": "ruff check",
                        "language": "python",
                    },
                ],
            },
        ],
    }
    write_config(config_file, config)

    tmp_config_file = write_tmp_pre_commit_config_without_excludes(config_file)

    assert tmp_config_file == Path("Test_directory/tmp.pre-commit-config.yaml")
    assert load_config(tmp_config_file) == {
        "repos": [
            {
                "repo": "meta",
                "hooks": [
                    {
                        "id": "check-hooks-apply",
                    },
                ],
            },
            {
                "repo": "local",
                "hooks": [
                    {
                        "id": "check-snake-case",
                        "name": "check snake case",
                        "entry": "python3 foo.py",
                        "language": "python",
                    },
                    {
                        "id": "ruff",
                        "name": "ruff",
                        "entry": "ruff check",
                        "language": "python",
                    },
                ],
            },
        ],
    }
    assert load_config(config_file) == config


def test_run_pre_commit_should_return_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    command = []

    def fake_run(
        args: list[str | Path],
        *,
        check: bool,
        capture_output: bool,
    ) -> subprocess.CompletedProcess:
        command.extend(args)
        assert check is False
        assert capture_output is True
        return subprocess.CompletedProcess(args, returncode=0)

    monkeypatch.setattr("pre_commit_excludes.remove_unnecessary_excludes.subprocess.run", fake_run)

    assert (
        run_pre_commit(
            Path("/usr/bin/prek"),
            Path("Test_directory/tmp.pre-commit-config.yaml"),
            "check-snake-case",
            [Path("foo.py"), Path("bar.py")],
        )
        == 0
    )
    assert command == [
        Path("/usr/bin/prek"),
        "run",
        "--config",
        "Test_directory/tmp.pre-commit-config.yaml",
        "check-snake-case",
        "--files",
        Path("foo.py"),
        Path("bar.py"),
    ]
