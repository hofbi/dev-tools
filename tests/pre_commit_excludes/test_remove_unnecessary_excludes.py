from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call

import pytest
from pre_commit_excludes.hook_utils import Hook, load_config, write_config
from pre_commit_excludes.remove_unnecessary_excludes import (
    CLITools,
    SkippedExclude,
    find_unnecessary_excludes,
    get_files_from_exclude_path,
    get_hooks_to_cleanup,
    is_exclude_unnecessary,
    parse_skipped_exclude,
    remove_excludes_from_config,
    run_pre_commit,
    write_tmp_pre_commit_config_without_excludes,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


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


def test_is_exclude_unnecessary_when_pre_commit_succeeds_should_return_true(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exclude = Path("Repo/excluded")
    excluded_file = exclude / "foo.py"
    fs.create_file(excluded_file)
    tools = CLITools(pre_commit=Path("/usr/bin/prek"), git=Path("/usr/bin/git"))
    run_pre_commit_mock = MagicMock(return_value=0)
    undo_changes_mock = MagicMock()
    monkeypatch.setattr("pre_commit_excludes.remove_unnecessary_excludes.run_pre_commit", run_pre_commit_mock)
    monkeypatch.setattr("pre_commit_excludes.remove_unnecessary_excludes.undo_changes", undo_changes_mock)

    assert is_exclude_unnecessary("ruff", exclude, Path("tmp-pre-commit-config.yaml"), tools, verbose=True)
    run_pre_commit_mock.assert_called_once_with(
        tools.pre_commit, Path("tmp-pre-commit-config.yaml"), "ruff", [excluded_file], verbose=True
    )
    undo_changes_mock.assert_not_called()


def test_is_exclude_unnecessary_when_pre_commit_fails_should_restore_and_return_false(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exclude = Path("Repo/excluded")
    excluded_file = exclude / "foo.py"
    fs.create_file(excluded_file)
    tools = CLITools(pre_commit=Path("/usr/bin/prek"), git=Path("/usr/bin/git"))
    run_pre_commit_mock = MagicMock(return_value=1)
    undo_changes_mock = MagicMock()
    monkeypatch.setattr("pre_commit_excludes.remove_unnecessary_excludes.run_pre_commit", run_pre_commit_mock)
    monkeypatch.setattr("pre_commit_excludes.remove_unnecessary_excludes.undo_changes", undo_changes_mock)

    assert not is_exclude_unnecessary("ruff", exclude, Path("tmp-pre-commit-config.yaml"), tools)
    run_pre_commit_mock.assert_called_once_with(
        tools.pre_commit, Path("tmp-pre-commit-config.yaml"), "ruff", [excluded_file], verbose=False
    )
    undo_changes_mock.assert_called_once_with(exclude, tools.git)


def test_find_unnecessary_excludes_should_return_only_unnecessary_excludes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unnecessary_exclude = Path("Repo/unnecessary.py")
    necessary_exclude = Path("Repo/necessary.py")
    temporary_config = Path("Repo/tmp.pre-commit-config.yaml")
    tools = CLITools(pre_commit=Path("/usr/bin/prek"), git=Path("/usr/bin/git"))
    is_exclude_unnecessary_mock = MagicMock(side_effect=[True, False])
    monkeypatch.setattr(
        "pre_commit_excludes.remove_unnecessary_excludes.is_exclude_unnecessary",
        is_exclude_unnecessary_mock,
    )

    result = find_unnecessary_excludes(
        [Hook("ruff", [unnecessary_exclude, necessary_exclude])],
        temporary_config,
        set(),
        tools,
        verbose=True,
    )

    assert dict(result) == {"ruff": [unnecessary_exclude]}
    assert is_exclude_unnecessary_mock.call_args_list == [
        call("ruff", unnecessary_exclude, temporary_config, tools, verbose=True),
        call("ruff", necessary_exclude, temporary_config, tools, verbose=True),
    ]


def test_find_unnecessary_excludes_should_skip_only_matching_hook_and_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_exclude = Path("Repo/shared.py")
    temporary_config = Path("Repo/tmp.pre-commit-config.yaml")
    tools = CLITools(pre_commit=Path("/usr/bin/prek"), git=Path("/usr/bin/git"))
    is_exclude_unnecessary_mock = MagicMock(return_value=True)
    monkeypatch.setattr(
        "pre_commit_excludes.remove_unnecessary_excludes.is_exclude_unnecessary",
        is_exclude_unnecessary_mock,
    )

    result = find_unnecessary_excludes(
        [Hook("ruff", [shared_exclude]), Hook("black", [shared_exclude])],
        temporary_config,
        {SkippedExclude("ruff", shared_exclude)},
        tools,
    )

    assert dict(result) == {"black": [shared_exclude]}
    is_exclude_unnecessary_mock.assert_called_once_with("black", shared_exclude, temporary_config, tools, verbose=False)


def test_find_unnecessary_excludes_when_all_excludes_are_skipped_should_return_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exclude = Path("Repo/skipped.py")
    tools = CLITools(pre_commit=Path("/usr/bin/prek"), git=Path("/usr/bin/git"))
    is_exclude_unnecessary_mock = MagicMock()
    monkeypatch.setattr(
        "pre_commit_excludes.remove_unnecessary_excludes.is_exclude_unnecessary",
        is_exclude_unnecessary_mock,
    )

    result = find_unnecessary_excludes(
        [Hook("ruff", [exclude])],
        Path("Repo/tmp.pre-commit-config.yaml"),
        {SkippedExclude("ruff", exclude)},
        tools,
    )

    assert dict(result) == {}
    is_exclude_unnecessary_mock.assert_not_called()


def test_remove_excludes_from_config_should_remove_matching_lines_from_each_hook(fs: FakeFilesystem) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    fs.create_file(
        config_file,
        contents="""repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
            generated/foo\\.py|
            generated/keep.py|
            generated/bar.py
          )
      - id: black
        exclude: |
          (?x)^(
            generated/foo.py|
            generated/keep.py
          )
""",
    )

    remove_excludes_from_config(
        config_file,
        {
            "ruff": [Path("Repo/generated/foo.py"), Path("Repo/generated/bar.py")],
            "black": [Path("Repo/generated/foo.py")],
        },
    )

    assert (
        config_file.read_text(encoding="utf-8")
        == """repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
            generated/keep.py
          )
      - id: black
        exclude: |
          (?x)^(
            generated/keep.py
          )
"""
    )


def test_remove_excludes_from_config_should_repair_separator_when_removing_final_alternative(
    fs: FakeFilesystem,
) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    fs.create_file(
        config_file,
        contents="""repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
            generated/keep.py|  # Still required.
            generated/remove.py
          )
""",
    )

    remove_excludes_from_config(config_file, {"ruff": [Path("Repo/generated/remove.py")]})

    assert "            generated/keep.py  # Still required.\n" in config_file.read_text(encoding="utf-8")


def test_remove_excludes_from_config_should_match_directory_without_trailing_slash(fs: FakeFilesystem) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    fs.create_file(
        config_file,
        contents="""repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
            generated/remove/|
            generated/keep/
          )
""",
    )

    remove_excludes_from_config(config_file, {"ruff": [Path("Repo/generated/remove")]})

    assert "generated/remove/" not in config_file.read_text(encoding="utf-8")


def test_remove_excludes_from_config_should_only_change_exclude_block_for_matching_hook(
    fs: FakeFilesystem,
) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    original_config = """repos:
  - repo: local
    hooks:
      - id: ruff
        args:
          - generated/remove.py
        exclude: generated/remove.py
      - id: black
        exclude: |
          (?x)^(
            generated/remove.py
          )
"""
    fs.create_file(config_file, contents=original_config)

    remove_excludes_from_config(config_file, {"ruff": [Path("Repo/generated/remove.py")]})

    assert config_file.read_text(encoding="utf-8") == original_config


def test_remove_excludes_from_config_should_preserve_detected_yaml_formatting(fs: FakeFilesystem) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    fs.create_file(
        config_file,
        contents="""# Project hooks
repos:
- repo: 'local' # Keep this comment.
  hooks:
  - id: ruff
    exclude: |
      (?x)^(
        generated/remove.py|
        generated/keep.py
      )
""",
    )

    remove_excludes_from_config(config_file, {"ruff": [Path("Repo/generated/remove.py")]})

    assert (
        config_file.read_text(encoding="utf-8")
        == """# Project hooks
repos:
- repo: 'local' # Keep this comment.
  hooks:
  - id: ruff
    exclude: |
      (?x)^(
        generated/keep.py
      )
"""
    )


def test_remove_excludes_from_config_when_every_entry_is_removed_should_leave_empty_wrapper(
    fs: FakeFilesystem,
) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    fs.create_file(
        config_file,
        contents="""repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
            generated/remove.py
          )
""",
    )

    remove_excludes_from_config(config_file, {"ruff": [Path("Repo/generated/remove.py")]})

    assert (
        config_file.read_text(encoding="utf-8")
        == """repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
          )
"""
    )


def test_remove_excludes_from_config_for_empty_removals_should_leave_config_unchanged(fs: FakeFilesystem) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    original_config = "repos: []\n"
    fs.create_file(config_file, contents=original_config)

    remove_excludes_from_config(config_file, {})

    assert config_file.read_text(encoding="utf-8") == original_config


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
