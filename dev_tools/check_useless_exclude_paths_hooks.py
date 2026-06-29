# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

import sys
from pathlib import Path
from typing import Any

from pre_commit_excludes.hook_utils import load_hooks

CONFIG_FILE = ".pre-commit-config.yaml"


def have_non_existent_paths_or_duplicates(hooks_list: list[Any]) -> bool:
    non_existing_paths: list[tuple[str, str]] = [
        (hook_instance.id, path)
        for hook_instance in hooks_list
        if hook_instance.has_non_existing_paths()
        for path in hook_instance.find_non_existing_paths()
    ]
    duplicates: list[tuple[str, str]] = [
        (hook_instance.id, duplicate)
        for hook_instance in hooks_list
        if hook_instance.has_duplicates()
        for duplicate in hook_instance.find_duplicates()
    ]

    if non_existing_paths:
        print(f"Remove the following non-existing exclusions in {CONFIG_FILE}:")
        for hook_id, path in non_existing_paths:
            print(f"In hook {hook_id}: {str(path).split('Repo/', 1)[-1]}")

    if duplicates:
        print(f"Remove the following duplicates from the exclusions in {CONFIG_FILE}:")
        for hook_id, duplicate in duplicates:
            print(f"In hook {hook_id}: {str(duplicate).split('Repo/', 1)[-1]}")

    return bool(non_existing_paths or duplicates)


def main() -> int:
    repo_root = Path.cwd()
    pre_commit_config = repo_root / CONFIG_FILE
    hooks_list = load_hooks(repo_root, pre_commit_config)
    return 1 if have_non_existent_paths_or_duplicates(hooks_list) else 0


if __name__ == "__main__":
    sys.exit(main())
