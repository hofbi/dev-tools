# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.
"""Print the GitHub owner of an item (folder or file).

Can also find owners of children, if a level is given.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from whoowns.ownership_utils import GithubOwnerShip, check_git


def main() -> int:
    args = parse_arguments()

    owners = get_owners(args.item, args.level)
    if not owners:
        print(
            "No ownership assigned.\nGo to https://docs.github.com/articles/about-code-owners to learn how to assign code ownership."
        )
        return 1

    print_owners(owners)
    return 0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "item",
        type=Path,
        help="Path to the item (file or folder) to query ownership for",
    )
    parser.add_argument(
        "-l",
        "--level",
        type=int,
        help="Level/depth to descend into the folder",
        default=0,
    )

    return parser.parse_args()


def get_subitems(item: Path, level: int) -> list[Path]:
    if level == 0:
        return [item.resolve()]
    pattern = "/".join(["*"] * level)
    return sorted(item.resolve() for item in item.glob(pattern))


def get_owners(item: Path, level: int) -> dict[str, tuple[str, ...]]:
    if not item.exists():
        msg = f"Item {item} does not exist. Please provide a valid path to an existing file or folder as item."
        raise FileNotFoundError(msg)

    repo_dir = Path(check_git("rev-parse --show-toplevel", repo_dir=item.parent if item.is_file() else item).rstrip())

    if (codeowners_file := find_codeowners_file(repo_dir)) is None:
        return {}

    items = get_subitems(item, level)
    ownership = GithubOwnerShip(repo_dir, codeowners_file)
    return {str(item.relative_to(repo_dir)): ownership.get_owners(item) for item in items}


def find_codeowners_file(repo_dir: Path) -> Path | None:
    relative_codeowner_paths = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]
    for relative_path in relative_codeowner_paths:
        codeowners_file = repo_dir / relative_path
        if codeowners_file.exists():
            return codeowners_file

    print(f"Error: No CODEOWNERS file found (candidates: {', '.join(relative_codeowner_paths)}).")
    return None


def print_owners(owners: dict[str, tuple[str, ...]]) -> None:
    max_path_length = max((len(item) for item in owners), default=0)
    for item, owner in owners.items():
        print(f"{item:{max_path_length}} -> {', '.join(owner)}")


if __name__ == "__main__":
    sys.exit(main())
