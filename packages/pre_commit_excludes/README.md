# Pre-Commit-Excludes

[![PyPI](https://img.shields.io/pypi/v/pre-commit-excludes)](https://pypi.org/project/pre-commit-excludes/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pre-commit-excludes)](https://pypi.org/project/pre-commit-excludes/)
[![PyPI - License](https://img.shields.io/pypi/l/pre-commit-excludes)](https://pypi.org/project/pre-commit-excludes/)

## Remove Unnecessary Excludes

`remove-unnecessary-excludes` finds lines in your exclude list that are no longer required and removes them from the supplied `.pre-commit-config.yaml`.
The tool checks each exclude by running the affected hook without excludes and restores changes made by a failing hook when the exclude is still required.

> [!NOTE]
> This hook deliberately only supports simple `|`-separated lists of file paths in `exclude` fields — complex regular expressions are not supported.
> Each path must be on its own line in a multiline YAML block scalar; compact inline exclude patterns are not rewritten.
> Keeping exclusions as plain `|`-separated paths also makes it easier for humans to maintain an overview of what is excluded.

```shell
# Cleanup the entire config for all hooks
uvx --from pre-commit-excludes remove-unnecessary-excludes .pre-commit-config.yaml --pre-commit-binary prek --git-binary git --all

# Cleanup only specific hooks such as typos and ruff-check
uvx --from pre-commit-excludes remove-unnecessary-excludes .pre-commit-config.yaml --pre-commit-binary prek --git-binary git --hook typos --hook ruff-check

# Skip excludes that you want to keep
uvx --from pre-commit-excludes remove-unnecessary-excludes .pre-commit-config.yaml --pre-commit-binary prek --git-binary git --all --skip-exclude "check-json:tests/invalid.json"
```

## Restrict Folder Excludes

`restrict-folder-excludes` restricts excluded folders in the `.pre-commit-config.yaml` exclude list from a very broad folder exclude to more fine granular excludes.

```shell
# Restrict all excluded folders for all hooks
uvx --from pre-commit-excludes restrict-folder-excludes .pre-commit-config.yaml --all

# Restrict all excluded folders for specific hooks such as typos and ruff-check and skip the tests folder for check-json
uvx --from pre-commit-excludes restrict-folder-excludes .pre-commit-config.yaml --hook typos --hook ruff-check --skip-exclude "check-json:tests"
```

Example for the command above

```yaml
# Before
exclude: |
  (?x)^(
    foo|
    bar
  )

# After
exclude: |
  (?x)^(
    foo/a|
    foo/b|
    foo/c|
    foo/foo.txt|
    foo/README.md|
    bar/a|
    bar/bar.txt
  )
```
