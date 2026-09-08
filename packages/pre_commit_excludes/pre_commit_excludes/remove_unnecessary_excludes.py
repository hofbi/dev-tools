"""Remove unnecessary excludes from a .pre-commit-config.yaml."""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString

from pre_commit_excludes.args import SkippedExclude, create_default_parser
from pre_commit_excludes.hook_utils import (
    Hook,
    get_hook_configs_from_all_repos,
    get_hooks_to_cleanup,
    get_relative_excludes_by_hook,
    get_skipped_excludes_relative_to_config,
    load_config,
    load_hooks,
    load_round_trip_config,
    write_config,
)


@dataclass(frozen=True)
class CLITools:
    """Binaries used to find the excludes."""

    pre_commit: Path
    git: Path


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
) -> list[Hook]:
    hooks_with_unnecessary_excludes = []
    for hook in hooks_to_cleanup:
        unnecessary_excludes = [
            exclude
            for exclude in hook.exclude_paths
            if SkippedExclude(hook.id, exclude) not in skipped_excludes
            and is_exclude_unnecessary(hook.id, exclude, pre_commit_config_without_excludes, tools, verbose=verbose)
        ]
        if unnecessary_excludes:
            hooks_with_unnecessary_excludes.append(Hook(hook.id, unnecessary_excludes))
    return hooks_with_unnecessary_excludes


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


def remove_excludes_from_config(config_file: Path, hooks_to_update: list[Hook]) -> None:
    """Remove matching exclude lines from hooks in a pre-commit config."""
    config, yaml = load_round_trip_config(config_file)
    relative_excludes = get_relative_excludes_by_hook(hooks_to_update, config_file.parent)
    if _remove_excludes_from_hooks(config, relative_excludes):
        yaml.dump(config, config_file)


def parse_arguments() -> argparse.Namespace:
    parser = create_default_parser(__doc__)
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
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    pre_commit_config_without_excludes = write_tmp_pre_commit_config_without_excludes(args.config)
    cli_tools = CLITools(args.pre_commit_binary, args.git_binary)
    hooks_with_excludes = load_hooks(args.config.parent, args.config)
    hooks_to_cleanup = hooks_with_excludes if args.all else get_hooks_to_cleanup(hooks_with_excludes, args.hook)
    skipped_excludes = get_skipped_excludes_relative_to_config(args.skip_exclude, args.config.parent)

    hooks_with_unnecessary_excludes = find_unnecessary_excludes(
        hooks_to_cleanup, pre_commit_config_without_excludes, skipped_excludes, cli_tools, verbose=args.verbose
    )
    pre_commit_config_without_excludes.unlink()

    print()
    print("Excludes to remove:")
    print({hook.id: hook.exclude_paths for hook in hooks_with_unnecessary_excludes})
    remove_excludes_from_config(args.config, hooks_with_unnecessary_excludes)

    return 0


if __name__ == "__main__":
    sys.exit(main())
