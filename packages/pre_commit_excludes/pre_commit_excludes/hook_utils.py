from __future__ import annotations

import itertools
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString
from ruamel.yaml.util import load_yaml_guess_indent

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping, MutableMapping


@dataclass(frozen=True)
class SkippedExclude:
    """A pair of hook ID and exclude path that should be skipped from removal."""

    hook_id: str
    path: Path


class Hook:
    """Represent a pre-commit hook with its excluded paths."""

    def __init__(self, id: str, exclude_paths: list[Path]) -> None:
        self.__id = id
        self.__exclude_paths = exclude_paths

    @classmethod
    def from_hook_config(cls: type[Hook], root_directory: Path, hook_config: dict[str, str]) -> Hook:
        excluded_paths_list = [
            root_directory / Path(exclude) for exclude in extract_literal_exclude_paths(hook_config["exclude"])
        ]

        return cls(hook_config["id"], excluded_paths_list)

    @property
    def id(self) -> str:
        return self.__id

    @property
    def exclude_paths(self) -> list[Path]:
        return self.__exclude_paths

    def find_duplicates(self) -> list[Path]:
        counter = Counter(self.exclude_paths)

        return [path for path in counter if counter[path] > 1]

    def find_non_existing_paths(self) -> list[Path]:
        return [path for path in self.exclude_paths if not path.resolve().exists()]

    def has_duplicates(self) -> bool:
        return bool(self.find_duplicates())

    def has_non_existing_paths(self) -> bool:
        return bool(self.find_non_existing_paths())

    def count_excluded_files(self) -> int:
        existing_paths = [path for path in self.exclude_paths if path.exists()]
        total_file_count = sum(1 for path in existing_paths if path.is_file())
        excluded_dirs = [path for path in existing_paths if path.is_dir()]
        total_dir_count = sum(
            sum(1 for file in excluded_dir.rglob("*") if file.is_file()) for excluded_dir in excluded_dirs
        )
        return total_file_count + total_dir_count


def is_regex_pattern(exclude: str) -> bool:
    return any(regex_key in exclude for regex_key in ["*", "$", "^"])


def extract_literal_exclude_paths(exclude_regex: str) -> list[str]:
    exclude_list = (
        _remove_verbose_regex_comments(exclude_regex)
        .replace("\n", "")
        .replace(" ", "")
        .replace("(?x)^(", "")
        .replace("^", "")
        .replace(r"\.", ".")
        .replace(")", "")
        .split("|")
    )

    return [exclude for exclude in exclude_list if not is_regex_pattern(exclude)]


def _remove_verbose_regex_comments(exclude: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in exclude.splitlines())


def has_excludes(hook_config: dict[str, str]) -> bool:
    return bool(hook_config.get("exclude")) and hook_config.get("exclude") != "^$"


def load_config(config_file: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    config = yaml.load(config_file.read_text(encoding="utf-8"))

    return config if isinstance(config, dict) else {}


def write_config(config_file: Path, config: dict[str, Any]) -> None:
    yaml = YAML(typ="safe")
    with config_file.open("w", encoding="utf-8") as output:
        yaml.dump(config, output)


def get_hook_configs_from_all_repos(config: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    return itertools.chain.from_iterable(repo["hooks"] for repo in config["repos"])


def load_hooks(root_directory: Path, config_file: Path) -> list[Hook]:
    config = load_config(config_file)
    hook_configs = get_hook_configs_from_all_repos(config)

    return [Hook.from_hook_config(root_directory, hook) for hook in hook_configs if has_excludes(hook)]


def get_hooks_to_cleanup(hooks: list[Hook], selected_hooks: list[str] | None) -> list[Hook]:
    if selected_hooks is None:
        return []

    return [hook for hook in hooks if hook.id in selected_hooks]


def get_relative_excludes_by_hook(hooks: list[Hook], root_directory: Path) -> dict[str, list[str]]:
    """Return hook excludes as config-relative POSIX paths grouped by hook ID."""
    relative_excludes: dict[str, list[str]] = {}
    for hook in hooks:
        relative_excludes.setdefault(hook.id, []).extend(
            exclude.relative_to(root_directory).as_posix() for exclude in hook.exclude_paths
        )
    return relative_excludes


def get_skipped_excludes_relative_to_config(
    skipped_excludes: list[SkippedExclude], pre_commit_config_parent: Path
) -> set[SkippedExclude]:
    return {
        SkippedExclude(skipped_exclude.hook_id, pre_commit_config_parent / skipped_exclude.path)
        for skipped_exclude in skipped_excludes
    }


def load_round_trip_config(config_file: Path) -> tuple[CommentedMap, YAML]:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = sys.maxsize
    original_content = config_file.read_text(encoding="utf-8")
    config, indent, block_sequence_indent = load_yaml_guess_indent(original_content, yaml=yaml)
    if indent is not None:
        yaml.indent(sequence=indent, offset=block_sequence_indent)
    return (config if isinstance(config, CommentedMap) else CommentedMap()), yaml


def update_config_hook_excludes(
    config_file: Path,
    update_exclude: Callable[[MutableMapping[str, Any]], str | None],
) -> None:
    """Apply exclude replacements to hooks and write the config if it changed."""
    config, yaml = load_round_trip_config(config_file)
    changed = False
    for hook_config in get_hook_configs_from_all_repos(config):
        updated_exclude = update_exclude(hook_config)
        if updated_exclude is not None and updated_exclude != hook_config.get("exclude"):
            hook_config["exclude"] = LiteralScalarString(updated_exclude)
            changed = True

    if changed:
        yaml.dump(config, config_file)
