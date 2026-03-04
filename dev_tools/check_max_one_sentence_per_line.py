from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

from dev_tools.git_hook_utils import parse_arguments

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    changed = fix_files_with_multiple_sentences_per_line(args.filenames)
    return 1 if changed else 0


def fix_files_with_multiple_sentences_per_line(files: list[Path]) -> bool:
    pattern = re.compile(r"(```.*?```)|(?<=[A-Za-z][.?!]) +(?=[A-Z])", re.DOTALL)

    def replacement_function(match: re.Match[str]) -> str:
        # If code block matched (group 1), return it unchanged
        if match.group(1):
            return match.group(1)
        # Otherwise, it's a sentence boundary - replace with newline
        return "\n"

    files_changed_state = [fix_file_with_multiple_sentences_per_line(file, pattern, replacement_function) for file in files]
    return any(files_changed_state)


def fix_file_with_multiple_sentences_per_line(file: Path, pattern: re.Pattern[str], replacement_function: callable[[re.Match[str]], str]) -> bool:
    old_content = file.read_text()


    if (new_content := pattern.sub(replacement_function, old_content)) != old_content:
        file.write_text(new_content)
        return True

    return False


if __name__ == "__main__":
    sys.exit(main())
