from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pre_commit_excludes.hook_utils import Hook, SkippedExclude
from pre_commit_excludes.restrict_folder_excludes import restrict_folder_excludes, update_config_with_stricter_excludes

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


def test_restrict_folder_excludes_for_folder_should_replace_folder_with_direct_children(fs: FakeFilesystem) -> None:
    exclude_folder = Path("Repo/excluded")
    first_file = exclude_folder / "foo.py"
    nested_folder = exclude_folder / "nested"
    second_file = nested_folder / "bar.py"
    fs.create_file(first_file)
    fs.create_file(second_file)

    hooks = [Hook("ruff", [exclude_folder])]
    restricted_hooks = restrict_folder_excludes(hooks, set())

    assert len(restricted_hooks) == 1
    assert restricted_hooks[0].id == "ruff"
    assert restricted_hooks[0].exclude_paths == [first_file, nested_folder]
    assert hooks[0].exclude_paths == [exclude_folder]


def test_restrict_folder_excludes_for_file_should_keep_file(fs: FakeFilesystem) -> None:
    exclude_file = Path("Repo/excluded.py")
    fs.create_file(exclude_file)

    restricted_hooks = restrict_folder_excludes([Hook("ruff", [exclude_file])], set())

    assert restricted_hooks[0].exclude_paths == [exclude_file]


def test_restrict_folder_excludes_for_skipped_folder_should_keep_folder(fs: FakeFilesystem) -> None:
    exclude_folder = Path("Repo/excluded")
    fs.create_file(exclude_folder / "foo.py")
    skipped_excludes = {SkippedExclude("ruff", exclude_folder)}

    restricted_hooks = restrict_folder_excludes([Hook("ruff", [exclude_folder])], skipped_excludes)

    assert restricted_hooks[0].exclude_paths == [exclude_folder]


def test_restrict_folder_excludes_should_only_skip_matching_hook_and_path(fs: FakeFilesystem) -> None:
    shared_exclude_folder = Path("Repo/excluded")
    excluded_file = shared_exclude_folder / "foo.py"
    fs.create_file(excluded_file)
    hooks = [Hook("ruff", [shared_exclude_folder]), Hook("black", [shared_exclude_folder])]

    restricted_hooks = restrict_folder_excludes(hooks, {SkippedExclude("ruff", shared_exclude_folder)})

    assert restricted_hooks[0].exclude_paths == [shared_exclude_folder]
    assert restricted_hooks[1].exclude_paths == [excluded_file]


def test_update_config_with_stricter_excludes_should_update_matching_hooks(fs: FakeFilesystem) -> None:
    config_file = Path("Repo/.pre-commit-config.yaml")
    fs.create_file(
        config_file,
        contents="""# Keep this comment.
repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
            generated|
            keep
          )
      - id: black
        exclude: 'unchanged.py'
""",
    )

    update_config_with_stricter_excludes(
        config_file,
        [Hook("ruff", [Path("Repo/generated/foo.py"), Path("Repo/generated/bar.py")])],
    )

    assert (
        config_file.read_text(encoding="utf-8")
        == """# Keep this comment.
repos:
  - repo: local
    hooks:
      - id: ruff
        exclude: |
          (?x)^(
            generated/foo.py|
            generated/bar.py
          )
      - id: black
        exclude: 'unchanged.py'
"""
    )
