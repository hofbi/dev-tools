from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from dev_tools.sync_tool_versions import SyncEntry, VersionSyncSpec, main, sync_versions

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


def test_sync_tool_versions_supports_glob_paths(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root / "packages" / "one")
    fs.create_dir(repo_root / "packages" / "two")
    first_file = repo_root / "packages" / "one" / "pyproject.toml"
    second_file = repo_root / "packages" / "two" / "pyproject.toml"
    ignored_file = repo_root / "packages" / "two" / "README.md"

    first_file.write_text('target-version = "py313"\n')
    second_file.write_text('target-version = "py313"\n')
    ignored_file.write_text('target-version = "py313"\n')

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "python",
                    "version": "3.14",
                    "entries": [
                        {
                            "path": "packages/**/pyproject.toml",
                            "pattern": 'target-version\\s*=\\s*"py([0-9]+)"',
                            "version_override": "314",
                        }
                    ],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])

    assert result == 1
    assert first_file.read_text() == 'target-version = "py314"\n'
    assert second_file.read_text() == 'target-version = "py314"\n'
    assert ignored_file.read_text() == 'target-version = "py313"\n'


def test_sync_tool_versions_for_glob_match_without_pattern_should_skip_file(
    capsys: pytest.CaptureFixture[str],
    fs: FakeFilesystem,
) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root / "packages" / "one")
    fs.create_dir(repo_root / "packages" / "two")
    matching_file = repo_root / "packages" / "one" / "pyproject.toml"
    non_matching_file = repo_root / "packages" / "two" / "pyproject.toml"

    matching_file.write_text('target-version = "py313"\n')
    non_matching_file.write_text('requires-python = ">=3.13"\n')

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "python",
                    "version": "3.14",
                    "entries": [
                        {
                            "path": "packages/**/pyproject.toml",
                            "pattern": 'target-version\\s*=\\s*"py([0-9]+)"',
                            "version_override": "314",
                        }
                    ],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert output == ""
    assert matching_file.read_text() == 'target-version = "py314"\n'
    assert non_matching_file.read_text() == 'requires-python = ">=3.13"\n'


def test_sync_tool_versions_for_glob_without_any_pattern_match_should_report_error(
    capsys: pytest.CaptureFixture[str],
    fs: FakeFilesystem,
) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root / "packages" / "one")
    fs.create_dir(repo_root / "packages" / "two")
    first_file = repo_root / "packages" / "one" / "pyproject.toml"
    second_file = repo_root / "packages" / "two" / "pyproject.toml"

    first_file.write_text('requires-python = ">=3.13"\n')
    second_file.write_text('requires-python = ">=3.13"\n')

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "python",
                    "version": "3.14",
                    "entries": [
                        {
                            "path": "packages/**/pyproject.toml",
                            "pattern": 'target-version\\s*=\\s*"py([0-9]+)"',
                            "version_override": "314",
                        }
                    ],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert "pattern did not match in any files matched by" in output
    assert "packages/**/pyproject.toml" in output
    assert first_file.read_text() == 'requires-python = ">=3.13"\n'
    assert second_file.read_text() == 'requires-python = ">=3.13"\n'


def test_sync_tool_versions_for_unmatched_glob_should_report_error(
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
                    "name": "python",
                    "version": "3.14",
                    "entries": [
                        {
                            "path": "packages/**/pyproject.toml",
                            "pattern": 'target-version\\s*=\\s*"py([0-9]+)"',
                        }
                    ],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert "missing file" in output
    assert "packages/**/pyproject.toml" in output


def test_sync_tool_versions_supports_the_version_placeholder(fs: FakeFilesystem) -> None:
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
                    "entries": [{"path": "MODULE.bazel", "pattern": 'RUST_VERSION\\s*=\\s*"THE_VERSION"'}],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])

    assert result == 1
    assert module_file.read_text() == 'RUST_VERSION = "1.91.0"\n'


def test_sync_tool_versions_placeholder_matches_semver_variants(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    versions_file = repo_root / "versions.txt"
    versions_file.write_text("v1.2.3\n1.2.3-rc.1\n1.2.3+build.5\n")

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "rust",
                    "version": "2.0.0",
                    "entries": [{"path": "versions.txt", "pattern": "THE_VERSION"}],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])

    assert result == 1
    assert versions_file.read_text() == "2.0.0\n2.0.0\n2.0.0\n"


def test_sync_tool_versions_placeholder_allows_version_override(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    versions_file = repo_root / "versions.txt"
    versions_file.write_text("py3.14\n")

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "python",
                    "version": "3.14",
                    "entries": [
                        {
                            "path": "versions.txt",
                            "pattern": "py([0-9.]+)",
                            "version_override": "314",
                        }
                    ],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])

    assert result == 1
    assert versions_file.read_text() == "py314\n"


def test_sync_tool_versions_placeholder_rejects_non_semver(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    versions_file = repo_root / "versions.txt"
    versions_file.write_text("1.2\n1.2.3.4\n")

    config_path = repo_root / ".versions.yaml"
    _write_versions_config(
        config_path,
        {
            "name": "tool-versions",
            "sync_versions": [
                {
                    "name": "rust",
                    "version": "2.0.0",
                    "entries": [{"path": "versions.txt", "pattern": "THE_VERSION"}],
                },
            ],
        },
    )

    result = main(["--config", str(config_path)])

    assert result == 1
    assert versions_file.read_text() == "1.2\n1.2.3.4\n"


def test_sync_tool_versions_placeholder_must_be_unique(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    versions_file = repo_root / "versions.txt"
    versions_file.write_text("1.2.3\n")

    spec = VersionSyncSpec(
        name="rust",
        version="2.0.0",
        entries=[
            SyncEntry(path=versions_file, pattern="THE_VERSION and THE_VERSION"),
        ],
    )
    changed, errors = sync_versions([spec])

    assert not changed
    assert errors


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


def test_sync_tool_versions_for_missing_config_should_report_error(
    capsys: pytest.CaptureFixture[str],
    fs: FakeFilesystem,
) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root)
    config_path = repo_root / ".versions.yaml"

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 1
    assert "config file not found" in output


def test_sync_tool_versions_for_empty_sync_versions_should_noop(
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
            "sync_versions": [],
        },
    )

    result = main(["--config", str(config_path)])
    output = capsys.readouterr().out

    assert result == 0
    assert output == ""


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


def test_sync_versions_for_glob_match_without_pattern_should_skip_file(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root / "packages" / "one")
    fs.create_dir(repo_root / "packages" / "two")
    matching_file = repo_root / "packages" / "one" / "pyproject.toml"
    non_matching_file = repo_root / "packages" / "two" / "pyproject.toml"

    matching_file.write_text('target-version = "py313"\n')
    non_matching_file.write_text('requires-python = ">=3.13"\n')

    spec = VersionSyncSpec(
        name="python",
        version="3.14",
        entries=[
            SyncEntry(
                path=Path("packages/**/pyproject.toml"),
                pattern='target-version\\s*=\\s*"py([0-9]+)"',
                version_override="314",
                base_dir=repo_root,
            )
        ],
    )
    changed, errors = sync_versions([spec])

    assert changed
    assert errors == []
    assert matching_file.read_text() == 'target-version = "py314"\n'
    assert non_matching_file.read_text() == 'requires-python = ">=3.13"\n'


def test_sync_versions_for_glob_without_any_pattern_match_should_return_error(fs: FakeFilesystem) -> None:
    repo_root = Path("Repo")
    fs.create_dir(repo_root / "packages" / "one")
    fs.create_dir(repo_root / "packages" / "two")
    first_file = repo_root / "packages" / "one" / "pyproject.toml"
    second_file = repo_root / "packages" / "two" / "pyproject.toml"

    first_file.write_text('requires-python = ">=3.13"\n')
    second_file.write_text('requires-python = ">=3.13"\n')

    spec = VersionSyncSpec(
        name="python",
        version="3.14",
        entries=[
            SyncEntry(
                path=Path("packages/**/pyproject.toml"),
                pattern='target-version\\s*=\\s*"py([0-9]+)"',
                version_override="314",
                base_dir=repo_root,
            )
        ],
    )
    changed, errors = sync_versions([spec])

    assert not changed
    assert errors
    assert "pattern did not match in any files matched by" in errors[0]
    assert first_file.read_text() == 'requires-python = ">=3.13"\n'
    assert second_file.read_text() == 'requires-python = ">=3.13"\n'


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
