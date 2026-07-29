# Pre-Commit-Excludes

<!-- rumdl-disable MD013 -->
[![PyPI](https://img.shields.io/pypi/v/pre-commit-excludes)](https://pypi.org/project/pre-commit-excludes/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pre-commit-excludes)](https://pypi.org/project/pre-commit-excludes/)
[![PyPI - License](https://img.shields.io/pypi/l/pre-commit-excludes)](https://pypi.org/project/pre-commit-excludes/)
<!-- rumdl-enable MD013 -->

`remove-unnecessary-excludes` should help you to find lines in your exclude list that are no longer required.
Running this tool will try to remove excludes from your config by removing a line, running the hook, and restore the old config if it is still required.

Right now this is in early development, so we don't automatically update the `.pre-commit-config.yaml` with all unnecessary excludes removed.
Instead, we only print which excludes can be removed for which hook.
More automation will come in future releases.

> [!NOTE]
> This hook deliberately only supports simple `|`-separated lists of file paths in `exclude` fields — complex regular expressions are not supported.
> Keeping exclusions as plain `|`-separated paths also makes it easier for humans to maintain an overview of what is excluded.

## Usage

```shell
# Cleanup the entire config for all hooks
uvx remove-unnecessary-excludes .pre-commit-config.yaml --pre-commit-binary prek --git-binary git --all

# Cleanup only specific hooks such as typos and ruff-check
uvx remove-unnecessary-excludes .pre-commit-config.yaml --pre-commit-binary prek --git-binary git --hook typos --hook ruff-check
```
