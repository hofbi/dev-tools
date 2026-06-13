from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

PRE_COMMIT_CONFIG_FILE = ".pre-commit-config.yaml"
PRE_COMMIT_MANIFEST_FILE = ".pre-commit-hooks.yaml"


def _load_yaml_file(file_path: Path) -> Any:  # noqa: ANN401
    yaml = YAML(typ="safe")
    return yaml.load(file_path.read_text(encoding="utf-8"))


def get_hooks_manifest(repo_root: Path | None = None) -> list[dict[str, object]]:
    if repo_root is None:
        repo_root = Path.cwd()

    hooks_manifest = repo_root / PRE_COMMIT_MANIFEST_FILE
    parsed = _load_yaml_file(hooks_manifest)
    return parsed if isinstance(parsed, list) else []


def get_hook_by_id(hook_id: str) -> dict[str, object]:
    for hook in get_hooks_manifest():
        if hook["id"] == hook_id:
            return hook
    msg = f"{hook_id} not found in hooks manifest"
    raise ValueError(msg)
