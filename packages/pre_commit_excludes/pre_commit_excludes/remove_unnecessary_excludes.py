"""Remove unnecessary excludes from a .pre-commit-config.yaml."""

import argparse
import subprocess
import sys
from pathlib import Path

from pre_commit_excludes.hook_utils import Hook, load_config, load_hooks, write_config


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


def run_prek(pre_commit_binary: Path, pre_commit_config: Path, hook_id: str, files: list[Path]) -> int:
    return subprocess.check_call(
        [pre_commit_binary, "run", "--config", str(pre_commit_config), hook_id, "--files", *files],
    )


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
        help="Path to the pre-commit compatible binary used to run hooks.",
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
    hooks_with_excludes = load_hooks(args.config.parent, args.config)
    hooks_to_cleanup = hooks_with_excludes if args.all else get_hooks_to_cleanup(hooks_with_excludes, args.hook)

    print(pre_commit_config_without_excludes)
    print(hooks_to_cleanup)

    return 0


if __name__ == "__main__":
    sys.exit(main())
