from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

RULE_PATTERN = re.compile(r"(?m)(?<![A-Za-z0-9_])(?P<rule>[A-Za-z_][A-Za-z0-9_]*)\s*\(")


@dataclass(frozen=True)
class RuleCall:
    """A parsed Bazel rule call."""

    rule_kind: str
    body: str


def remove_comments(content: str) -> str:
    return re.sub(r"(?m)#.*$", "", content)


def find_rule_calls(content: str, rule_name: str | None = None) -> Iterator[RuleCall]:
    content_without_comments = remove_comments(content)

    for match in RULE_PATTERN.finditer(content_without_comments):
        if rule_name is not None and match.group("rule") != rule_name:
            continue

        open_parens_count = 1
        current_index = match.end()

        while current_index < len(content_without_comments) and open_parens_count > 0:
            character = content_without_comments[current_index]
            if character == "(":
                open_parens_count += 1
            elif character == ")":
                open_parens_count -= 1
            current_index += 1

        if open_parens_count == 0:
            yield RuleCall(
                rule_kind=match.group("rule"),
                body=content_without_comments[match.end() : current_index - 1],
            )


def rule_has_tag(rule_body: str, tag: str) -> bool:
    tags_pattern = re.compile(r'(?ms)(?<![A-Za-z0-9_])tags\s*=\s*\[[^\]]*["\']' + re.escape(tag) + r'["\']')
    return bool(tags_pattern.search(remove_comments(rule_body)))
