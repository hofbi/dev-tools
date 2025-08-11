from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from pre_commit.constants import CONFIG_FILE

from dev_tools.check_useless_exclude_paths_hooks import Hook, load_hooks


def parse_arguments() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--output-file", type=Path, default=None)
    return parser.parse_args()


def create_excluded_files_report(hooks_list: list[Hook]) -> dict:
    hook_metrics_with_excluded_files: list[dict] = [
        {"hook_id": hook.id, "excluded_files_count": hook.count_excluded_files()}
        for hook in hooks_list
        if hook.count_excluded_files() > 0
    ]
    return {
        "total_excluded_files": sum(
            hook_metric["excluded_files_count"] for hook_metric in hook_metrics_with_excluded_files
        ),
        "hooks": hook_metrics_with_excluded_files,
    }


def main() -> int:
    args = parse_arguments()
    repo_root = Path.cwd()
    pre_commit_config = repo_root / CONFIG_FILE
    hooks_list = load_hooks(repo_root, pre_commit_config)
    output_data = create_excluded_files_report(hooks_list)

    json_output = json.dumps(output_data, indent=2)
    print(json_output)
    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(json_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
