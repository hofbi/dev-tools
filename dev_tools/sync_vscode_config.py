#!/usr/bin/env python

# Copyright (c) Luminar Technologies, Inc. All rights reserved.
# Licensed under the MIT License.

from __future__ import annotations

import argparse
import json  # for writing JSON, we need a pretty printer. PyJSON5 doesn't support this: https://github.com/Kijewski/pyjson5/issues/19#issuecomment-970504400
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyjson5  # for parsing comments, we need JSON5

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_INDENT = 4


@dataclass
class DictOverwriteRecord:
    key: str
    old_value: Any
    new_value: Any


def load_devcontainer_config(devcontainer_json_path: Path) -> Any:  # noqa: ANN401
    return pyjson5.loads(devcontainer_json_path.read_text())["customizations"]["vscode"]


def get_and_set(dict: Any, key: Any, value: Any) -> Any:  # noqa: ANN401
    old_value = dict.get(key, None)
    dict[key] = value
    return old_value


def update_dict_overwriting_values(dict: Any, new_values_dict: dict) -> list[DictOverwriteRecord]:  # noqa: ANN401
    overwrite_records = []
    for key, value in new_values_dict.items():
        old_value = get_and_set(dict, key, value)
        if old_value is not None and old_value != value:
            overwrite_records.append(DictOverwriteRecord(key, old_value, value))
    return overwrite_records


def combine_lists_without_duplicates(
    old_values: Any,  # noqa: ANN401
    new_values_list: list,
) -> list[str]:
    combined_set = set(old_values) | set(new_values_list)
    return sorted(combined_set)


def write_vscode_json(json_path: Path, json_dict: dict, indent: int) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(json_dict, indent=indent, ensure_ascii=False) + "\n")


def update_vscode_settings_json(
    settings_json: Path, settings_dict: dict, indent: int = DEFAULT_INDENT
) -> list[DictOverwriteRecord]:
    old_settings_dict = pyjson5.loads(settings_json.read_text()) if settings_json.is_file() else {}
    overwrite_records = update_dict_overwriting_values(old_settings_dict, settings_dict)
    write_vscode_json(settings_json, old_settings_dict, indent=indent)

    return overwrite_records


def get_extension_recommendations(extensions_dict: Any) -> list[str]:  # noqa: ANN401
    recommendations = extensions_dict.get("recommendations", [])
    if not isinstance(recommendations, list):
        msg = "Invalid settings.json: recommendations must be a list"
        raise TypeError(msg)
    for item in recommendations:
        if not isinstance(item, str):
            msg = f"Invalid settings.json: recommendations must be a list of strings. Bad item: '{item}'"
            raise TypeError(msg)
    return recommendations


def filter_out_unwanted_recommendations(recommendations: list[str]) -> list[str]:
    # extensions.json's unwantedRecommendations are not supported yet
    return [item for item in recommendations if not item.startswith("-")]


def update_vscode_extensions_json(
    extensions_json: Path, extensions_list: list[str], indent: int = DEFAULT_INDENT
) -> None:
    old_extensions_dict = pyjson5.loads(extensions_json.read_text()) if extensions_json.is_file() else {}
    old_extensions_list = get_extension_recommendations(old_extensions_dict)
    old_extensions_dict["recommendations"] = combine_lists_without_duplicates(
        old_extensions_list, filter_out_unwanted_recommendations(extensions_list)
    )
    write_vscode_json(extensions_json, old_extensions_dict, indent=indent)


def report_settings_findings(findings: list[DictOverwriteRecord], settings_json: Path) -> None:
    if any(findings):
        msg = f"Updated {settings_json}"
        logging.info(msg)
        for finding in findings:
            msg = f"In {settings_json}, '{finding.key}' was overwritten from '{finding.old_value}' to '{finding.new_value}'"
            logging.warning(msg)


def parse_arguments(args: Sequence[str] | None = None) -> argparse.Namespace:
    repo_root = Path.cwd()
    parser = argparse.ArgumentParser(description="Sync VS Code settings and extensions from devcontainer.json")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--devcontainer-json",
        type=Path,
        default=repo_root / ".devcontainer" / "devcontainer.json",
        help="Path to devcontainer.json",
    )
    parser.add_argument("--no-sync-settings", action="store_true", help="Don't sync settings.json")
    parser.add_argument(
        "--settings-path",
        type=Path,
        default=repo_root / ".vscode" / "settings.json",
        help="Path to settings.json which will contain merged settings",
    )
    parser.add_argument("--no-sync-extensions", action="store_true", help="Don't sync extensions.json")
    parser.add_argument(
        "--extensions-path",
        type=Path,
        default=repo_root / ".vscode" / "extensions.json",
        help="Path to extensions.json which will contain merged settings",
    )
    parser.add_argument("--indent", type=int, default=DEFAULT_INDENT, help="Indentation level for JSON output")
    return parser.parse_args(args)


def _should_sync_settings(args: argparse.Namespace) -> bool:
    return not args.no_sync_settings


def _should_sync_extensions(args: argparse.Namespace) -> bool:
    return not args.no_sync_extensions


def main() -> int:
    args = parse_arguments()
    lvl = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=lvl, format="%(asctime)s [%(levelname)s] %(message)s")

    msg = f"Syncing VS Code settings and extensions from {args.devcontainer_json} to {args.settings_path} and {args.extensions_path}"
    logging.info(msg)

    devcontainer_config = load_devcontainer_config(args.devcontainer_json)
    if _should_sync_settings(args):
        settings_findings = update_vscode_settings_json(
            args.settings_path, devcontainer_config.get("settings", {}), indent=args.indent
        )
        report_settings_findings(settings_findings, args.settings_path)

    if _should_sync_extensions(args):
        update_vscode_extensions_json(
            args.extensions_path, devcontainer_config.get("extensions", []), indent=args.indent
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
