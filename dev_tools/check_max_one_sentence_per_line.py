from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import regex

from dev_tools.git_hook_utils import parse_arguments

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

COMMON_ABBREVIATIONS = {
    # keep-sorted start
    "Dr",
    "e.g",
    "etc",
    "feat",
    "i.e",
    "Jr",
    "Mr",
    "Mrs",
    "Ms",
    "Prof",
    "Sr",
    "vs",
    # keep-sorted end
}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    changed = fix_files_with_multiple_sentences_per_line(args.filenames)
    return 1 if changed else 0


def fix_files_with_multiple_sentences_per_line(files: list[Path]) -> bool:
    code_block_pattern = r"```.*?```"
    abbreviations_pattern = "|".join(COMMON_ABBREVIATIONS)
    pattern = regex.compile(
        rf"({code_block_pattern})|(?<!(?:{abbreviations_pattern})\.)(?<=[A-Za-z][.?!]) +(?=[A-Z])", regex.DOTALL
    )

    def replacement_function(match: regex.Match[str]) -> str:
        # If code block matched (group 1), return it unchanged
        if match.group(1):
            return str(match.group(1))
        # Otherwise, it's a sentence boundary - replace with newline
        return "\n"

    files_changed_state = [
        fix_file_with_multiple_sentences_per_line(file, pattern, replacement_function) for file in files
    ]
    return any(files_changed_state)


def fix_file_with_multiple_sentences_per_line(
    file: Path, pattern: regex.Pattern[str], replacement_function: Callable[[regex.Match[str]], str]
) -> bool:
    old_content = file.read_text()

    if (new_content := pattern.sub(replacement_function, old_content)) != old_content:
        file.write_text(new_content)
        return True

    return False


if __name__ == "__main__":
    sys.exit(main())
