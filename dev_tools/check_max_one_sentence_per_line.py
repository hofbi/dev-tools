from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dev_tools.git_hook_utils import parse_arguments

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def line_has_multiple_sentences(line: str) -> bool:
    return bool(re.search(r"[A-Za-z][.?!] ", line))


def find_files_with_multiple_sentences_per_line(files: list[Path]) -> list[dict[str, object]]:
    incorrect_files = []
    for file in files:
        lines = file.read_text(errors="ignore").splitlines()
        for line_number, line in enumerate(lines, 1):
            if line_has_multiple_sentences(line):
                incorrect_files.append({"file_path": file, "line_number": line_number, "line_content": line.strip()})

    return incorrect_files


def has_any_file_multiple_sentences_per_line(files: list[Path]) -> bool:
    if incorrect_files := find_files_with_multiple_sentences_per_line(files):
        print("\nThe following lines contain multiple sentences (should be max one sentence per line):")
        for file in incorrect_files:
            print(f"{file['file_path']}:{file['line_number']}: error: '{file['line_content']}'")
        return True

    return False


def main(argv: Sequence[str] | None = None) -> int:
    return 1 if has_any_file_multiple_sentences_per_line(parse_arguments(argv).filenames) else 0


if __name__ == "__main__":
    raise SystemExit(main())
