#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    args = create_default_parser().parse_args(argv)
    changed = fix_files_with_multiple_sentences_per_line(args.filenames)
    return 1 if changed else 0


def create_default_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("filenames", nargs="*", type=Path)
    return parser


def fix_files_with_multiple_sentences_per_line(files: list[Path]) -> bool:
    pattern = re.compile(r"(?<=[A-Za-z][.?!]) +(?=[A-Z])")
    files_changed_state = [fix_file_with_multiple_sentences_per_line(file, pattern) for file in files]
    return any(files_changed_state)


def fix_file_with_multiple_sentences_per_line(file: Path, pattern: re.Pattern[str]) -> bool:
    old_content = file.read_text()

    if (new_content := pattern.sub("\n", old_content)) != old_content:
        file.write_text(new_content)
        return True

    return False


if __name__ == "__main__":
    sys.exit(main())
