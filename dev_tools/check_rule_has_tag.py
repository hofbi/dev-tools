from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

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


def _remove_comments(content: str) -> str:
    return re.sub(r"(?m)#.*$", "", content)


def find_rule_calls(content: str, rule_name: str) -> list[str]:
    content_without_comments = _remove_comments(content)
    rule_pattern = re.compile(rf"(?m)(?<![A-Za-z0-9_]){re.escape(rule_name)}\s*\(")
    rule_calls: list[str] = []

    for match in rule_pattern.finditer(content_without_comments):
        open_parens_count = 1
        current_index = match.end()

        while current_index < len(content_without_comments) and open_parens_count > 0:
            character = content_without_comments[current_index]
            if character == "(":
                open_parens_count += 1
            elif character == ")":
                open_parens_count -= 1
            current_index += 1

        if open_parens_count == 0:
            rule_calls.append(content_without_comments[match.end() : current_index - 1])

    return rule_calls


def rule_has_tag(rule_body: str, tag: str) -> bool:
    tags_pattern = re.compile(r'(?ms)(?<![A-Za-z0-9_])tags\s*=\s*\[[^\]]*["\']' + re.escape(tag) + r'["\']')
    return bool(tags_pattern.search(_remove_comments(rule_body)))


def is_rule_missing_tag(rule_body: str, tag: str) -> bool:
    return not rule_has_tag(rule_body, tag)


def find_invalid_files(filenames: Sequence[Path], rule_name: str, tag: str) -> list[Path]:
    return [
        filename
        for filename in filenames
        if (rule_calls := find_rule_calls(filename.read_text(), rule_name))
        and any(is_rule_missing_tag(rule_body, tag) for rule_body in rule_calls)
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
