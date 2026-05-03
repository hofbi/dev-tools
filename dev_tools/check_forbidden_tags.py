from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

from dev_tools.utils.build_file_parsing_utils import find_rule_calls, rule_has_tag
from dev_tools.utils.git_hook_utils import create_default_parser

if TYPE_CHECKING:
    import argparse
    from collections.abc import Sequence
    from pathlib import Path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = create_default_parser()
    parser.add_argument("--forbidden-tag", required=True)
    parser.add_argument("--allow-in-rule-kind")
    return parser.parse_args(argv)


def find_files_with_forbidden_tags(
    filenames: Sequence[Path],
    forbidden_tag: str,
    allowed_rule_kind_re: re.Pattern[str] | None,
) -> list[Path]:
    return [
        filename
        for filename in filenames
        if any(
            not (allowed_rule_kind_re and allowed_rule_kind_re.search(rule_call.rule_kind))
            and rule_has_tag(rule_call.body, forbidden_tag)
            for rule_call in find_rule_calls(filename.read_text())
        )
    ]


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    allowed_rule_kind_re = re.compile(args.allow_in_rule_kind) if args.allow_in_rule_kind else None
    invalid_files = find_files_with_forbidden_tags(args.filenames, args.forbidden_tag, allowed_rule_kind_re)

    for filename in invalid_files:
        if args.allow_in_rule_kind:
            print(
                f"Error: {filename} contains a rule with `tags` containing `{args.forbidden_tag}` outside "
                f"a rule kind matching /{args.allow_in_rule_kind}/."
            )
        else:
            print(f"Error: {filename} contains a rule with `tags` containing `{args.forbidden_tag}`.")

    return 1 if invalid_files else 0


if __name__ == "__main__":
    sys.exit(main())
