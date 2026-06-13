from __future__ import annotations

from pathlib import Path

from pre_commit.clientlib import load_manifest
from pre_commit.constants import MANIFEST_FILE


def get_hooks_manifest(repo_root: Path | None = None) -> list[dict]:
    if repo_root is None:
        repo_root = Path.cwd()

    hooks_manifest = repo_root / MANIFEST_FILE
    return list(load_manifest(hooks_manifest))


def get_hook_by_id(hook_id: str) -> dict:
    for hook in get_hooks_manifest():
        if hook["id"] == hook_id:
            return hook
    msg = f"{hook_id} not found in hooks manifest"
    raise ValueError(msg)
