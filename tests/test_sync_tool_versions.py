from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from dev_tools.sync_tool_versions import SyncEntry, VersionSyncSpec, main, prepare_sync, sync_versions

if TYPE_CHECKING:
    import pytest
    from pyfakefs.fake_filesystem import FakeFilesystem


def _write_versions_config(config_path: Path, data: dict) -> None:
    yaml = YAML()
    yaml.dump(data, config_path)


def test_sync_tool_versions_for_multiple_matches_should_update_all(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    module_file = repo_root / "MODULE.bazel"
    pre_commit_config = repo_root / ".pre-commit-config.yaml"

    module_file.write_text('RUST_VERSION = "1.87.0"\n')
    pre_commit_config.write_text("rust: 1.87.0\nrust: 1.87.0\n")

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "rust",
                    "version": "1.91.0",
                    "entries": [
                        {"path": "MODULE.bazel", "pattern": 'RUST_VERSION\\s*=\\s*"([^"]+)"'},
                        {"path": ".pre-commit-config.yaml", "pattern": "rust:\\s*([0-9.]+)"},
                    ],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])

    assert result == 1
    assert module_file.read_text() == 'RUST_VERSION = "1.91.0"\n'
    assert pre_commit_config.read_text() == "rust: 1.91.0\nrust: 1.91.0\n"


def test_sync_tool_versions_for_missing_file_should_report_error(
    capsys: pytest.CaptureFixture[str],
    fs: FakeFilesystem,
) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "rust",
                    "version": "1.91.0",
                    "entries": [{"path": "missing.txt", "pattern": "rust:\\s*([0-9.]+)"}],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert "missing file" in output
    assert "missing.txt" in output


def test_sync_tool_versions_for_pattern_no_match_should_report_error(
    capsys: pytest.CaptureFixture[str],
    fs: FakeFilesystem,
) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    module_file = repo_root / "MODULE.bazel"
    module_file.write_text('RUST_VERSION = "1.87.0"\n')

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "rust",
                    "version": "1.91.0",
                    "entries": [{"path": "MODULE.bazel", "pattern": "NO_MATCH([0-9.]+)"}],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert "did not match" in output
    assert "MODULE.bazel" in output


def test_sync_tool_versions_for_pattern_without_capture_group_should_report_error(
    capsys: pytest.CaptureFixture[str],
    fs: FakeFilesystem,
) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    module_file = repo_root / "MODULE.bazel"
    module_file.write_text('RUST_VERSION = "1.87.0"\n')

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "rust",
                    "version": "1.91.0",
                    "entries": [{"path": "MODULE.bazel", "pattern": 'RUST_VERSION\\s*=\\s*"[0-9.]+"'}],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert "capture group" in output


def test_sync_tool_versions_for_missing_top_level_name_should_report_error(
    capsys: pytest.CaptureFixture[str],
    fs: FakeFilesystem,
) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "sync_versions": [
                {
                    "name": "rust",
                    "version": "1.91.0",
                    "entries": [{"path": "MODULE.bazel", "pattern": 'RUST_VERSION\\s*=\\s*"([0-9.]+)"'}],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert "top-level 'name'" in output


def test_prepare_sync_for_missing_file_should_return_error(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)

    spec = VersionSyncSpec(
        name="rust",
        version="1.91.0",
        entries=[SyncEntry(path=repo_root / "missing.txt", pattern="rust:\\s*([0-9.]+)")],
    )
    regex, content, errors = prepare_sync(spec, spec.entries[0])

    assert regex is None
    assert content is None
    assert errors


def test_prepare_sync_for_valid_entry_should_return_regex_and_content(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    module_file = repo_root / "MODULE.bazel"
    module_file.write_text('RUST_VERSION = "1.87.0"\n')

    spec = VersionSyncSpec(
        name="rust",
        version="1.91.0",
        entries=[SyncEntry(path=module_file, pattern='RUST_VERSION\\s*=\\s*"([0-9.]+)"')],
    )
    regex, content, errors = prepare_sync(spec, spec.entries[0])

    assert errors == []
    assert content == 'RUST_VERSION = "1.87.0"\n'
    assert regex is not None


def test_sync_versions_for_valid_spec_should_update_content(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    module_file = repo_root / "MODULE.bazel"
    module_file.write_text('RUST_VERSION = "1.87.0"\n')

    spec = VersionSyncSpec(
        name="rust",
        version="1.91.0",
        entries=[SyncEntry(path=module_file, pattern='RUST_VERSION\\s*=\\s*"([0-9.]+)"')],
    )
    changed, errors = sync_versions([spec])

    assert changed
    assert errors == []
    assert module_file.read_text() == 'RUST_VERSION = "1.91.0"\n'


def test_sync_versions_for_missing_file_should_return_error(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)

    spec = VersionSyncSpec(
        name="rust",
        version="1.91.0",
        entries=[SyncEntry(path=repo_root / "missing.txt", pattern="rust:\\s*([0-9.]+)")],
    )
    changed, errors = sync_versions([spec])

    assert not changed
    assert errors
