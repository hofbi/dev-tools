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
    parser.add_argument("--rule-path", type=str, required=True)
    parser.add_argument("--rule-name", type=str, required=True)
    return parser.parse_args(argv)


def has_wrong_load_statement(content: str, rule_path: str, rule_name: str) -> bool:
    invalid_pattern = rf'^\s*load\((?!"{re.escape(rule_path)}")[^)]*"{re.escape(rule_name)}"[^)]*\)'
    return bool(re.search(invalid_pattern, content, re.MULTILINE))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)

    invalid_files: list[Path] = [
        filename
        for filename in args.filenames
        if has_wrong_load_statement(filename.read_text(), args.rule_path, args.rule_name)
    ]
    for filename in invalid_files:
        print(
            f"Error: {filename} does not use the correct load statement. "
            f'Please use `load("{args.rule_path}", "{args.rule_name}")` to load the rule "{args.rule_name}".'
        )

    return 1 if invalid_files else 0


if __name__ == "__main__":
    sys.exit(main())
