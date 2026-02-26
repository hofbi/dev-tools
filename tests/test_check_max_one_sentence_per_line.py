from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from dev_tools.check_max_one_sentence_per_line import main

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.mark.parametrize(
    ("input", "expected_output", "expected_return"),
    [
        pytest.param(
            "This. Splits.",
            "This.\nSplits.",
            1,
            id="fixes_two_sentences",
        ),
        pytest.param(
            "One long, long sentence with many words.",
            "One long, long sentence with many words.",
            0,
            id="no_issues",
        ),
        pytest.param(
            "This is a sentence. This is another sentence. And another.",
            "This is a sentence.\nThis is another sentence.\nAnd another.",
            1,
            id="fixes_three_sentences",
        ),
        pytest.param(
            "1. this is an enumeration\n2. This is another item",
            "1. this is an enumeration\n2. This is another item",
            0,
            id="does_not_split_enumeration",
        ),
        pytest.param(
            "This is a sentence! Is this another? Yes.",
            "This is a sentence!\nIs this another?\nYes.",
            1,
            id="fixes_sentences_with_different_punctuation",
        ),
        pytest.param(
            "This is a sentence.  This is another.",
            "This is a sentence.\nThis is another.",
            1,
            id="fixes_sentences_with_multiple_spaces",
        ),
        pytest.param(
            "Do not split abbreviations like e.g. or i.e. or Dr. in the middle of a sentence.",
            "Do not split abbreviations like e.g. or i.e. or Dr. in the middle of a sentence.",
            0,
            id="does_not_split_sentences_with_predefined_abbreviations",
        ),
        pytest.param(
            "Limitation: split abbreviations followed by a space and a capital letter such as Dr. Hyde.",
            "Limitation: split abbreviations followed by a space and a capital letter such as Dr.\nHyde.",
            1,
            id="does_split_sentences_with_abbreviations_followed_by_a_space_and_capital_letter",
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

    assert main([str(file)]) == expected_return
    assert file.read_text() == expected_output


def test_multiple_files_one_failing(fs: FakeFilesystem) -> None:
    file_a = Path("Repo/file_a.md")
    file_b = Path("Repo/file_b.md")
    fs.create_file(file_a, contents="This. Splits.")
    fs.create_file(file_b, contents="One sentence.")

    assert main([str(file_a), str(file_b)]) == 1
    assert file_a.read_text() == "This.\nSplits."
    assert file_b.read_text() == "One sentence."
