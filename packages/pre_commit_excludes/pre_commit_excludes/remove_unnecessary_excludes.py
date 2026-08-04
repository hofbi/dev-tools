"""Remove unnecessary excludes from a .pre-commit-config.yaml."""

import argparse
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pre_commit_excludes.hook_utils import Hook, load_config, load_hooks, write_config


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

    excludes_to_remove = defaultdict(list)
    for hook in hooks_to_cleanup:
        for exclude in hook.exclude_paths:
            if SkippedExclude(hook.id, exclude) in skipped_excludes:
                continue

            if is_exclude_unnecessary(
                hook.id, exclude, pre_commit_config_without_excludes, cli_tools, verbose=args.verbose
            ):
                excludes_to_remove[hook.id].append(exclude)

    pre_commit_config_without_excludes.unlink()

    print()
    print("Excludes to remove:")
    print(excludes_to_remove)

    return 0


if __name__ == "__main__":
    sys.exit(main())
