from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from dev_tools.build_file_parsing_util import find_rule_calls, rule_has_tag
from dev_tools.git_hook_utils import create_default_parser

if TYPE_CHECKING:
    import argparse
    from collections.abc import Sequence
    from pathlib import Path


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = create_default_parser()
    parser.add_argument("--rule-name", type=str, required=True)
    parser.add_argument("--tag", type=str, required=True)
    return parser.parse_args(argv)


def is_rule_missing_tag(rule_body: str, tag: str) -> bool:
    return not rule_has_tag(rule_body, tag)


def find_invalid_files(filenames: Sequence[Path], rule_name: str, tag: str) -> list[Path]:
    return [
        filename
        for filename in filenames
        if any(
            is_rule_missing_tag(rule_call.body, tag) for rule_call in find_rule_calls(filename.read_text(), rule_name)
        )
    ]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    invalid_files = find_invalid_files(args.filenames, args.rule_name, args.tag)

    for filename in invalid_files:
        print(
            f"Error: {filename} contains a `{args.rule_name}` rule without `tags` containing `{args.tag}`. "
            f"Make sure you tag this rule with `{args.tag}`."
        )

    return 1 if invalid_files else 0


if __name__ == "__main__":
    sys.exit(main())
