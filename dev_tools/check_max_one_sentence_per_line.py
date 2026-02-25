from __future__ import annotations

import re
from argparse import ArgumentParser
from typing import TYPE_CHECKING

from dev_tools.git_hook_utils import create_default_parser

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def line_has_multiple_sentences(line: str) -> bool:
    return bool(re.search(r"[A-Za-z][.?!] ", line))


def split_sentences(line: str) -> list[str]:
    """Split a line into multiple sentences.

    Splits on letter followed by sentence-ending punctuation and space.
    Preserves leading whitespace from the original line.
    """
    # Get the leading whitespace
    leading_whitespace = line[: len(line) - len(line.lstrip())]

    # Split on the pattern: letter + sentence ending + space
    # Use lookahead to keep the punctuation with the sentence
    parts = re.split(r"(?<=[A-Za-z][.?!]) ", line.strip())

    # Add leading whitespace to each part except empty ones
    return [leading_whitespace + part if part else part for part in parts]


def find_files_with_multiple_sentences_per_line(files: list[Path]) -> list[dict[str, object]]:
    incorrect_files = []
    for file in files:
        lines = file.read_text(errors="ignore").splitlines()
        for line_number, line in enumerate(lines, 1):
            if line_has_multiple_sentences(line):
                incorrect_files.append({"file_path": file, "line_number": line_number, "line_content": line.strip()})

    return incorrect_files


def fix_files_with_multiple_sentences_per_line(files: list[Path]) -> bool:
    """Fix files by splitting lines with multiple sentences.

    Returns True if any files were modified, False otherwise.
    """
    modified = False
    for file in files:
        lines = file.read_text(errors="ignore").splitlines()
        new_lines = []
        file_modified = False

        for line in lines:
            if line_has_multiple_sentences(line):
                # Split the line into multiple sentences
                split_lines = split_sentences(line)
                new_lines.extend(split_lines)
                file_modified = True
            else:
                new_lines.append(line)

        if file_modified:
            file.write_text("\n".join(new_lines) + "\n" if new_lines else "", encoding="utf-8")
            modified = True

    return modified


def has_any_file_multiple_sentences_per_line(files: list[Path]) -> bool:
    if incorrect_files := find_files_with_multiple_sentences_per_line(files):
        print("\nThe following lines contain multiple sentences (should be max one sentence per line):")
        for file in incorrect_files:
            print(f"{file['file_path']}:{file['line_number']}: error: '{file['line_content']}'")
        return True

    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_default_parser()
    parser.add_argument("--fix", action="store_true", help="Automatically fix files by splitting multi-sentence lines")
    args = parser.parse_args(argv)

    if args.fix:
        modified = fix_files_with_multiple_sentences_per_line(args.filenames)
        return 1 if modified else 0

    return 1 if has_any_file_multiple_sentences_per_line(args.filenames) else 0


if __name__ == "__main__":
    raise SystemExit(main())
