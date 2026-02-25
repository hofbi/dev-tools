from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dev_tools.check_max_one_sentence_per_line import (
    find_files_with_multiple_sentences_per_line,
    has_any_file_multiple_sentences_per_line,
    line_has_multiple_sentences,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.mark.parametrize(
    "content",
    [
        "One sentence in this line.",
        "Here, too!",
        "And here?",
        "1. Must not match.",
        "2. Must also not match!",
        "No punctuation at all",
        "Sentence with comma, but no period",
    ],
)
def test_line_has_multiple_sentences_for_valid_content(content: str) -> None:
    assert not line_has_multiple_sentences(content)


@pytest.mark.parametrize(
    "content",
    [
        "This. Must match.",
        "Also this! one?",
        "And? This one.",
        "Do match abbr. because we shouldn't use them with a dot, but in all-caps.",
    ],
)
def test_line_has_multiple_sentences_for_invalid_content(content: str) -> None:
    assert line_has_multiple_sentences(content)


@pytest.mark.parametrize(
    "content",
    [
        "One sentence in this line.",
        "Here, too!",
        "And here?",
        "1. Must not match.",
        "2. Must also not match!",
    ],
)
def test_find_files_with_valid_content(fs: FakeFilesystem, content: str) -> None:
    fs.create_file(Path("Repo/file.md"), contents=content)

    assert find_files_with_multiple_sentences_per_line([Path("Repo/file.md")]) == []


@pytest.mark.parametrize(
    "content",
    [
        "This. Must match.",
        "Also this! one?",
        "And? This one.",
        "Do match abbr. because we shouldn't use them with a dot, but in all-caps.",
    ],
)
def test_find_files_with_invalid_content(fs: FakeFilesystem, content: str) -> None:
    fs.create_file(Path("Repo/file.md"), contents=content)

    assert find_files_with_multiple_sentences_per_line([Path("Repo/file.md")]) == [
        {"file_path": Path("Repo/file.md"), "line_number": 1, "line_content": content},
    ]


@pytest.mark.parametrize(
    "content",
    [
        "One sentence in this line.",
        "Here, too!",
        "And here?",
        "1. Must not match.",
        "2. Must also not match!",
    ],
)
def test_has_any_file_multiple_sentences_per_line_for_valid_content(
    fs: FakeFilesystem,
    content: str,
    capsys: pytest.CaptureFixture,
) -> None:
    fs.create_file(Path("Repo/file.md"), contents=content)

    assert not has_any_file_multiple_sentences_per_line([Path("Repo/file.md")])
    assert not capsys.readouterr().out


@pytest.mark.parametrize(
    "content",
    [
        "This. Must match.",
        "Also this! one?",
        "And? This one.",
        "Do match abbr. because we shouldn't use them with a dot, but in all-caps.",
    ],
)
def test_has_any_file_multiple_sentences_per_line_for_invalid_content(
    fs: FakeFilesystem,
    content: str,
    capsys: pytest.CaptureFixture,
) -> None:
    fs.create_file(Path("Repo/file.md"), contents=content)

    assert has_any_file_multiple_sentences_per_line([Path("Repo/file.md")])
    output = capsys.readouterr().out
    assert "multiple sentences" in output
    assert "max one sentence per line" in output
    assert content in output
