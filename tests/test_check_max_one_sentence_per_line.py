from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dev_tools.check_max_one_sentence_per_line import main

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.mark.parametrize(
    ("input", "expected_return", "expected_output"),
    [
        pytest.param(
            "This. Must match.",
            1,
            "This.\nMust match.",
            id="fixes_two_sentences",
        ),
        pytest.param(
            "One long, long sentence with many words.",
            0,
            "One long, long sentence with many words.",
            id="no_issues",
        ),
        pytest.param(
            "This is a sentence. This is another sentence. And another.",
            1,
            "This is a sentence.\nThis is another sentence.\nAnd another.",
            id="fixes_three_sentences",
        ),
        pytest.param(
            "1. this is an enumeration\n2. this is another item",
            0,
            "1. this is an enumeration\n2. this is another item",
            id="does_not_split_enumeration",
        ),
        pytest.param(
            "This is a sentence! Is this another? Yes.",
            1,
            "This is a sentence!\nIs this another?\nYes.",
            id="fixes_sentences_with_different_punctuation",
        ),
        pytest.param(
            "This is a sentence.  This is another.",
            1,
            "This is a sentence.\nThis is another.",
            id="fixes_sentences_with_multiple_spaces",
        ),
        pytest.param(
            "Do not split special abbreviations like e.g. or i.e. or Dr. in the middle of a sentence.",
            0,
            "Do not split special abbreviations like e.g. or i.e. or Dr. in the middle of a sentence.",
            id="does_not_split_sentences_with_predefined_abbreviations",
        ),
    ],
)
def test_main(
    fs: FakeFilesystem,
    input: str,
    expected_return: int,
    expected_output: str,
) -> None:
    file = Path("Repo/file.md")
    fs.create_file(file, contents=input)

    result = main([str(file)])

    assert result == expected_return
    content = file.read_text()
    assert content == expected_output


def test_multiple_files_one_failing(fs: FakeFilesystem) -> None:
    file_a = Path("Repo/file_a.md")
    file_b = Path("Repo/file_b.md")
    fs.create_file(file_a, contents="This. Must match.")
    fs.create_file(file_b, contents="One sentence.")

    assert main([str(file_a), str(file_b)]) == 1
    assert file_a.read_text() == "This.\nMust match."
    assert file_b.read_text() == "One sentence."
