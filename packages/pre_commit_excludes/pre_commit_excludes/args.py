from argparse import ArgumentParser, ArgumentTypeError
from pathlib import Path

from pre_commit_excludes.hook_utils import SkippedExclude


def parse_skipped_exclude(value: str) -> SkippedExclude:
    try:
        hook_id, exclude_path = value.split(":", maxsplit=1)
    except ValueError as error:
        msg = "expected HOOK_ID:EXCLUDE_PATH"
        raise ArgumentTypeError(msg) from error

    if not hook_id or not exclude_path:
        msg = "hook ID and exclude path must not be empty"
        raise ArgumentTypeError(msg)

    return SkippedExclude(hook_id, Path(exclude_path))


def create_default_parser(description: str) -> ArgumentParser:
    parser = ArgumentParser(description=description)
    parser.add_argument(
        "config",
        type=Path,
        help="Path to the .pre-commit-config.yaml that should be cleaned up.",
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
    return parser
