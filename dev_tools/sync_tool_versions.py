from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from dev_tools.git_hook_utils import create_default_parser

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Sequence


DEFAULT_CONFIG_FILE = ".versions.yaml"
VERSION_PLACEHOLDER = "THE_VERSION"
SEMVER_CAPTURE_GROUP = (
    r"(?<![0-9A-Za-z.-])"
    r"(v?(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-(?:(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?)"
    r"(?![0-9A-Za-z.-])"
)


@dataclass(frozen=True)
class SyncEntry:
    path: Path
    pattern: str
    version_override: str | None = None


@dataclass(frozen=True)
class VersionSyncSpec:
    name: str
    version: str
    entries: list[SyncEntry]


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = create_default_parser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.cwd() / DEFAULT_CONFIG_FILE,
        help=f"Path to the versions config file (default: {DEFAULT_CONFIG_FILE})",
    )
    return parser.parse_args(argv)


def _require_mapping(value: object, message: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(message)
    return value


def _require_list(value: object, message: str) -> list:
    if not isinstance(value, list):
        raise TypeError(message)
    return value


def _require_non_empty_str(value: object, message: str) -> str:
    if not isinstance(value, str):
        raise TypeError(message)
    if not value:
        raise ValueError(message)
    return value


def _parse_sync_entry(entry: dict, base_dir: Path, config_path: Path) -> SyncEntry:
    path_value = _require_non_empty_str(
        entry.get("path"),
        f"Each entries item must have a non-empty 'path' in {config_path}",
    )
    pattern = _require_non_empty_str(
        entry.get("pattern"),
        f"Each entries item must have a non-empty 'pattern' in {config_path}",
    )
    override = entry.get("version_override")
    if override is not None:
        override = _require_non_empty_str(
            override,
            f"Each entries item 'version_override' must be a non-empty string in {config_path}",
        )
    return SyncEntry(base_dir / Path(path_value), pattern, override)


def _parse_version_spec(entry: dict, base_dir: Path, config_path: Path) -> VersionSyncSpec:
    name = _require_non_empty_str(
        entry.get("name"),
        f"Each sync_versions entry must have a non-empty 'name' in {config_path}",
    )
    version = _require_non_empty_str(
        entry.get("version"),
        f"Each sync_versions entry must have a non-empty 'version' in {config_path}",
    )
    entries = _require_list(
        entry.get("entries"),
        f"Each sync_versions entry must have a non-empty 'entries' list in {config_path}",
    )
    if not entries:
        msg = f"Each sync_versions entry must have a non-empty 'entries' list in {config_path}"
        raise ValueError(msg)

    sync_entries = [
        _parse_sync_entry(
            _require_mapping(item, f"Each entries item must be a mapping in {config_path}"),
            base_dir,
            config_path,
        )
        for item in entries
    ]
    return VersionSyncSpec(name=name, version=version, entries=sync_entries)


def _load_config(config_path: Path) -> list[VersionSyncSpec]:
    yaml = YAML(typ="safe")
    data = yaml.load(config_path.read_text())
    data = _require_mapping(data, f"Top-level config must be a mapping in {config_path}")
    if "sync_versions" not in data:
        msg = f"Missing top-level 'sync_versions' in {config_path}"
        raise ValueError(msg)
    _require_non_empty_str(data.get("name"), f"Missing top-level 'name' in {config_path}")

    sync_versions = _require_list(data.get("sync_versions"), f"'sync_versions' must be a list in {config_path}")
    base_dir = config_path.parent
    return [
        _parse_version_spec(
            _require_mapping(item, f"Each sync_versions entry must be a mapping in {config_path}"),
            base_dir,
            config_path,
        )
        for item in sync_versions
    ]


def _replace_version(match: re.Match[str], version: str) -> str:
    start, end = match.span(1)
    rel_start = start - match.start(0)
    rel_end = end - match.start(0)
    original = match.group(0)
    return f"{original[:rel_start]}{version}{original[rel_end:]}"


def _make_replacer(version: str) -> Callable[[re.Match[str]], str]:
    def replace(match: re.Match[str]) -> str:
        return _replace_version(match, version)

    return replace


def prepare_sync(spec: VersionSyncSpec, entry: SyncEntry) -> tuple[re.Pattern[str] | None, str | None, list[str]]:
    errors: list[str] = []
    if not entry.path.is_file():
        errors.append(f"Error: sync_versions entry '{spec.name}' references missing file: {entry.path}")
        return None, None, errors

    pattern = entry.pattern
    if VERSION_PLACEHOLDER in pattern:
        if pattern.count(VERSION_PLACEHOLDER) != 1:
            errors.append(
                f"Error: sync_versions entry '{spec.name}' pattern must include {VERSION_PLACEHOLDER} exactly once "
                f"in {entry.path}: {entry.pattern}"
            )
            return None, None, errors
        pattern = pattern.replace(VERSION_PLACEHOLDER, SEMVER_CAPTURE_GROUP)

    try:
        regex = re.compile(pattern, re.MULTILINE)
    except re.error as exc:
        errors.append(f"Error: sync_versions entry '{spec.name}' has invalid pattern for {entry.path}: {exc}")
        return None, None, errors

    if regex.groups != 1:
        errors.append(
            f"Error: sync_versions entry '{spec.name}' pattern must have exactly one capture group "
            f"in {entry.path}: {entry.pattern}"
        )
        return None, None, errors

    content = entry.path.read_text()
    if not regex.search(content):
        errors.append(
            f"Error: sync_versions entry '{spec.name}' pattern did not match in {entry.path}: {entry.pattern}"
        )
        return None, None, errors

    return regex, content, errors


def sync_versions(specs: list[VersionSyncSpec]) -> tuple[bool, list[str]]:
    changed = False
    errors: list[str] = []
    targets = [(spec, entry) for spec in specs for entry in spec.entries]

    for spec, entry in targets:
        regex, content, entry_errors = prepare_sync(spec, entry)
        errors.extend(entry_errors)
        if regex is not None and content is not None:
            replacement_version = entry.version_override or spec.version
            new_content, _ = regex.subn(_make_replacer(replacement_version), content)
            if new_content != content:
                entry.path.write_text(new_content)
                changed = True

    return changed, errors


def _load_and_validate_config(config_path: Path) -> list[VersionSyncSpec] | None:
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}")
        return None

    try:
        specs = _load_config(config_path)
    except (TypeError, ValueError) as exc:
        print(f"Error: invalid config in {config_path}: {exc}")
        return None

    return specs


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    config_path = args.config

    specs = _load_and_validate_config(config_path)
    if specs is None:
        return 1

    changed, errors = sync_versions(specs)
    if errors:
        for error in errors:
            print(error)

    return 1 if changed or errors else 0


if __name__ == "__main__":
    sys.exit(main())
