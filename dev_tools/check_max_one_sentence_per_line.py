from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

from dev_tools.git_hook_utils import create_default_parser

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    args = create_default_parser().parse_args(argv)
    modified = fix_files_with_multiple_sentences_per_line(args.filenames)
    return 1 if modified else 0


def fix_files_with_multiple_sentences_per_line(files: list[Path]) -> bool:
    modified = False
    for file in files:
        lines = file.read_text(errors="ignore").splitlines()
        new_lines = []
        file_modified = False

        for line in lines:
            if _line_has_multiple_sentences(line):
                split_lines = _split_sentences(line)
                new_lines.extend(split_lines)
                file_modified = True
            else:
                new_lines.append(line)

        if file_modified:
            file.write_text("\n".join(new_lines) + "\n" if new_lines else "", encoding="utf-8")
            modified = True

    return modified


def _line_has_multiple_sentences(line: str) -> bool:
    return bool(re.search(r"[A-Za-z][.?!] ", line))


def _split_sentences(line: str) -> list[str]:
    leading_whitespace = line[: len(line) - len(line.lstrip())]

    parts = re.split(r"(?<=[A-Za-z][.?!]) ", line.strip())

    return [leading_whitespace + part if part else part for part in parts]


if __name__ == "__main__":
    sys.exit(main())
