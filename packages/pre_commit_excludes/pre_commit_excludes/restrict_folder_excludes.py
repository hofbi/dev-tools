"""Restrict folder excludes from a .pre-commit-config.yaml."""

import argparse
import sys
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from typing import Any

from pre_commit_excludes.args import create_default_parser
from pre_commit_excludes.hook_utils import (
    Hook,
    SkippedExclude,
    get_hooks_to_cleanup,
    get_relative_excludes_by_hook,
    get_skipped_excludes_relative_to_config,
    load_hooks,
    update_config_hook_excludes,
)


def _iter_restricted_excludes(hook: Hook, skipped_excludes: set[SkippedExclude]) -> Iterator[Path]:
    for exclude in hook.exclude_paths:
        if SkippedExclude(hook.id, exclude) in skipped_excludes or exclude.is_file():
            yield exclude
        else:
            yield from exclude.glob("*")


def restrict_folder_excludes(hooks_to_restrict: list[Hook], skipped_excludes: set[SkippedExclude]) -> list[Hook]:
    """Replace directory excludes with excludes for each direct child in the directory."""
    return [Hook(hook.id, list(_iter_restricted_excludes(hook, skipped_excludes))) for hook in hooks_to_restrict]


def update_config_with_stricter_excludes(config_file: Path, restricted_hooks: list[Hook]) -> None:
    """Update the exclude blocks for the restricted hooks in a pre-commit config."""
    excludes_by_hook = get_relative_excludes_by_hook(restricted_hooks, config_file.parent)

    def update_exclude(hook_config: MutableMapping[str, Any]) -> str | None:
        hook_id = hook_config.get("id")
        if hook_id not in excludes_by_hook:
            return None

        excludes = excludes_by_hook[hook_id]
        return (
            "\n".join(
                [
                    "(?x)^(",
                    *(
                        f"  {exclude}{'|' if index < len(excludes) - 1 else ''}"
                        for index, exclude in enumerate(excludes)
                    ),
                    ")",
                ]
            )
            + "\n"
        )

    update_config_hook_excludes(config_file, update_exclude)


def parse_arguments() -> argparse.Namespace:
    parser = create_default_parser(__doc__)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    hooks_with_excludes = load_hooks(args.config.parent, args.config)
    hooks_to_restrict = hooks_with_excludes if args.all else get_hooks_to_cleanup(hooks_with_excludes, args.hook)
    skipped_excludes = get_skipped_excludes_relative_to_config(args.skip_exclude, args.config.parent)

    restricted_hooks = restrict_folder_excludes(hooks_to_restrict, skipped_excludes)
    update_config_with_stricter_excludes(args.config, restricted_hooks)

    return 0


if __name__ == "__main__":
    sys.exit(main())
