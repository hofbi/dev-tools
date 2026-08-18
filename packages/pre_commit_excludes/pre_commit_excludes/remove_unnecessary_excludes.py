"""Remove unnecessary excludes from a .pre-commit-config.yaml."""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString
from ruamel.yaml.util import load_yaml_guess_indent

from pre_commit_excludes.hook_utils import Hook, get_hook_configs_from_all_repos, load_config, load_hooks, write_config


@dataclass(frozen=True)
class SkippedExclude:
    """A pair of hook ID and exclude path that should be skipped from removal."""

    hook_id: str
    path: Path


@dataclass(frozen=True)
class CLITools:
    """Binaries used to find the excludes."""

    pre_commit: Path
    git: Path


def parse_skipped_exclude(value: str) -> SkippedExclude:
    try:
        hook_id, exclude_path = value.split(":", maxsplit=1)
    except ValueError as error:
        msg = "expected HOOK_ID:EXCLUDE_PATH"
        raise argparse.ArgumentTypeError(msg) from error

    if not hook_id or not exclude_path:
        msg = "hook ID and exclude path must not be empty"
        raise argparse.ArgumentTypeError(msg)

    return SkippedExclude(hook_id, Path(exclude_path))


def get_hooks_to_cleanup(hooks: list[Hook], selected_hooks: list[str] | None) -> list[Hook]:
    if selected_hooks is None:
        return []

    return [hook for hook in hooks if hook.id in selected_hooks]


def write_tmp_pre_commit_config_without_excludes(config_file: Path) -> Path:
    config = load_config(config_file)
    for repo in config["repos"]:
        for hook in repo["hooks"]:
            hook.pop("exclude", None)
    tmp_config = config_file.with_stem("tmp" + config_file.stem)
    write_config(tmp_config, config)
    return tmp_config


def get_files_from_exclude_path(exclude_path: Path) -> list[Path]:
    return [exclude_path] if exclude_path.is_file() else list(exclude_path.rglob("*"))


def run_pre_commit(
    pre_commit_binary: Path, pre_commit_config: Path, hook_id: str, files: list[Path], *, verbose: bool = False
) -> int:
    return subprocess.run(
        [pre_commit_binary, "run", "--config", str(pre_commit_config), hook_id, "--files", *files],
        check=False,
        capture_output=not verbose,
    ).returncode


def undo_changes(exclude_path: Path, git_binary) -> None:
    subprocess.run([git_binary, "restore", exclude_path], check=True)


def is_exclude_unnecessary(
    hook_id: str, exclude: Path, pre_commit_config_without_excludes: Path, tools: CLITools, *, verbose: bool = False
) -> bool:
    files = get_files_from_exclude_path(exclude)
    if run_pre_commit(tools.pre_commit, pre_commit_config_without_excludes, hook_id, files, verbose=verbose) == 0:
        return True
    undo_changes(exclude, tools.git)
    return False


def find_unnecessary_excludes(
    hooks_to_cleanup: list[Hook],
    pre_commit_config_without_excludes: Path,
    skipped_excludes: set[SkippedExclude],
    tools: CLITools,
    *,
    verbose: bool = False,
) -> defaultdict[str, list[Path]]:
    excludes_to_remove = defaultdict(list)
    for hook in hooks_to_cleanup:
        for exclude in hook.exclude_paths:
            if SkippedExclude(hook.id, exclude) in skipped_excludes:
                continue

            if is_exclude_unnecessary(hook.id, exclude, pre_commit_config_without_excludes, tools, verbose=verbose):
                excludes_to_remove[hook.id].append(exclude)
    return excludes_to_remove


def _exclude_line_value(line: str) -> str | None:
    value = line.split("#", maxsplit=1)[0].strip()
    if value.endswith("|"):
        value = value[:-1].rstrip()
    if not value or value in {"(?x)^(", ")"}:
        return None
    return Path(value.replace(r"\.", ".")).as_posix()


def _remove_trailing_separator(line: str) -> str:
    match = re.search(r"\|(?P<space>\s*)(?P<comment>#.*)?$", line)
    if match is None:
        return line
    comment = match.group("comment") or ""
    return f"{line[: match.start()]}{match.group('space')}{comment}"


def _remove_excludes_from_block(block: str, excludes: set[str]) -> str:
    lines = block.splitlines()
    retained_lines = [line for line in lines if _exclude_line_value(line) not in excludes]
    if len(retained_lines) == len(lines):
        return block

    alternative_indexes = [index for index, line in enumerate(retained_lines) if _exclude_line_value(line) is not None]
    if alternative_indexes:
        final_alternative = alternative_indexes[-1]
        retained_lines[final_alternative] = _remove_trailing_separator(retained_lines[final_alternative])
    trailing_newline = "\n" if block.endswith("\n") else ""
    return "\n".join(retained_lines) + trailing_newline


def _load_round_trip_config(content: str) -> tuple[CommentedMap, YAML]:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = sys.maxsize
    config, indent, block_sequence_indent = load_yaml_guess_indent(content, yaml=yaml)
    if indent is not None:
        yaml.indent(sequence=indent, offset=block_sequence_indent)
    return (config if isinstance(config, CommentedMap) else CommentedMap()), yaml


def _remove_excludes_from_hooks(config: CommentedMap, excludes_by_hook: dict[str, set[str]]) -> bool:
    changed = False
    hooks_to_update = [
        hook
        for hook in get_hook_configs_from_all_repos(config)
        if hook.get("id") in excludes_by_hook and isinstance(hook.get("exclude"), LiteralScalarString)
    ]
    for hook in hooks_to_update:
        hook_id = hook["id"]
        exclude = hook["exclude"]
        updated_exclude = _remove_excludes_from_block(exclude, excludes_by_hook[hook_id])
        if updated_exclude != exclude:
            hook["exclude"] = LiteralScalarString(updated_exclude)
            changed = True
    return changed


def remove_excludes_from_config(config_file: Path, excludes_to_remove: dict[str, list[Path]]) -> None:
    """Remove matching exclude lines from hooks in a pre-commit config."""
    relative_excludes = {
        hook_id: {exclude.relative_to(config_file.parent).as_posix() for exclude in excludes}
        for hook_id, excludes in excludes_to_remove.items()
    }
    original_content = config_file.read_text(encoding="utf-8")
    config, yaml = _load_round_trip_config(original_content)
    if _remove_excludes_from_hooks(config, relative_excludes):
        yaml.dump(config, config_file)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        type=Path,
        help="Path to the .pre-commit-config.yaml that should be cleaned up.",
    )
    parser.add_argument(
        "--pre-commit-binary",
        type=Path,
        required=True,
        help="Path to the pre-commit compatible binary (pre-commit or prek) used to run hooks.",
    )
    parser.add_argument(
        "--git-binary",
        type=Path,
        required=True,
        help="Path to the git binary used to undo local changes made by running the hooks.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output for debugging.",
    )
    parser.add_argument(
        "-s",
        "--skip-exclude",
        type=parse_skipped_exclude,
        nargs="+",
        default=[],
        metavar="HOOK_ID:EXCLUDE_PATH",
        help="Skip specific excludes from being removed using HOOK_ID:EXCLUDE_PATH.",
    )
    hook_group = parser.add_mutually_exclusive_group()
    hook_group.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Remove unnecessary excludes from all hooks in the config.",
    )
    hook_group.add_argument(
        "--hook",
        type=str,
        nargs="+",
        help="Remove unnecessary excludes from this specific hook.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    pre_commit_config_without_excludes = write_tmp_pre_commit_config_without_excludes(args.config)
    cli_tools = CLITools(args.pre_commit_binary, args.git_binary)
    hooks_with_excludes = load_hooks(args.config.parent, args.config)
    hooks_to_cleanup = hooks_with_excludes if args.all else get_hooks_to_cleanup(hooks_with_excludes, args.hook)
    skipped_excludes = {
        SkippedExclude(skipped_exclude.hook_id, args.config.parent / skipped_exclude.path)
        for skipped_exclude in args.skip_exclude
    }

    excludes_to_remove = find_unnecessary_excludes(
        hooks_to_cleanup, pre_commit_config_without_excludes, skipped_excludes, cli_tools, verbose=args.verbose
    )
    pre_commit_config_without_excludes.unlink()

    print()
    print("Excludes to remove:")
    print(excludes_to_remove)
    remove_excludes_from_config(args.config, excludes_to_remove)

    return 0


if __name__ == "__main__":
    sys.exit(main())
