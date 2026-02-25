from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dev_tools.check_max_one_sentence_per_line import (
    find_files_with_multiple_sentences_per_line,
    fix_files_with_multiple_sentences_per_line,
    has_any_file_multiple_sentences_per_line,
    line_has_multiple_sentences,
    main,
    split_sentences,
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


@pytest.mark.parametrize(
    ("input_text", "expected_output"),
    [
        ("This. Must match.", ["This.", "Must match."]),
        ("Also this! one?", ["Also this!", "one?"]),
        ("And? This one.", ["And?", "This one."]),
        ("Single sentence.", ["Single sentence."]),
        ("  Leading whitespace. Second sentence.", ["  Leading whitespace.", "  Second sentence."]),
        ("Three. Sentences. Here.", ["Three.", "Sentences.", "Here."]),
    ],
)
def test_split_sentences(input_text: str, expected_output: list[str]) -> None:
    assert split_sentences(input_text) == expected_output


def test_fix_files_with_multiple_sentences_per_line(fs: FakeFilesystem) -> None:
    fs.create_file(Path("Repo/file.md"), contents="This. Must match.\nAlready good.\nAlso this! one?")

    modified = fix_files_with_multiple_sentences_per_line([Path("Repo/file.md")])

    assert modified
    content = Path("Repo/file.md").read_text()
    assert content == "This.\nMust match.\nAlready good.\nAlso this!\none?\n"


def test_fix_files_with_multiple_sentences_per_line_no_changes(fs: FakeFilesystem) -> None:
    fs.create_file(Path("Repo/file.md"), contents="One sentence.\nAnother sentence.")

    modified = fix_files_with_multiple_sentences_per_line([Path("Repo/file.md")])

    assert not modified
    content = Path("Repo/file.md").read_text()
    assert content == "One sentence.\nAnother sentence."


def test_fix_files_preserves_leading_whitespace(fs: FakeFilesystem) -> None:
    fs.create_file(Path("Repo/file.md"), contents="  Indented. Second sentence.")

    modified = fix_files_with_multiple_sentences_per_line([Path("Repo/file.md")])

    assert modified
    content = Path("Repo/file.md").read_text()
    assert content == "  Indented.\n  Second sentence.\n"


def test_main_without_fix_flag_detects_issues(fs: FakeFilesystem) -> None:
    fs.create_file(Path("Repo/file.md"), contents="This. Must match.")

    result = main([str(Path("Repo/file.md"))])

    assert result == 1
    # Content should not be modified
    content = Path("Repo/file.md").read_text()
    assert content == "This. Must match."


def test_main_with_fix_flag_fixes_issues(fs: FakeFilesystem) -> None:
    fs.create_file(Path("Repo/file.md"), contents="This. Must match.")

    result = main(["--fix", str(Path("Repo/file.md"))])

    assert result == 1
    # Content should be modified
    content = Path("Repo/file.md").read_text()
    assert content == "This.\nMust match.\n"


def test_main_with_fix_flag_no_issues(fs: FakeFilesystem) -> None:
    fs.create_file(Path("Repo/file.md"), contents="One sentence.")

    result = main(["--fix", str(Path("Repo/file.md"))])

    assert result == 0
    # Content should not be modified
    content = Path("Repo/file.md").read_text()
    assert content == "One sentence."
