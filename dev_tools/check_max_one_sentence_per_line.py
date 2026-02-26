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
    changed = fix_files_with_multiple_sentences_per_line(args.filenames)
    return 1 if changed else 0


def fix_files_with_multiple_sentences_per_line(files: list[Path]) -> bool:
    changed = False
    pattern = re.compile(r"(?<=[A-Za-z][.?!]) +(?=[A-Z])")

    for file in files:
        new_content, number_of_replacements = pattern.subn("\n", file.read_text())

        if number_of_replacements:
            file.write_text(new_content)
            changed = True

    return changed


if __name__ == "__main__":
    sys.exit(main())
