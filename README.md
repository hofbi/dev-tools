# Dev Tools

[![Check](https://github.com/hofbi/dev-tools/actions/workflows/check.yaml/badge.svg)](https://github.com/hofbi/dev-tools/actions/workflows/check.yaml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/hofbi/dev-tools/master.svg)](https://results.pre-commit.ci/latest/github/hofbi/dev-tools/master)

This is a collection of Luminar's development tools.
These tools are used to help developers in their day-to-day tasks.

> [!NOTE]
> Since I was the main author of these tools while working at Luminar, I am maintaining this fork to keep them up to date. I try to contribute back if possible but since I am no longer working at Luminar, it is not guaranteed that my contributions are accepted.

<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=2 -->

- [Dev Tools](#dev-tools)
  - [Tools](#tools)
    - [Configure VS Code for Bazel](#configure-vs-code-for-bazel)
    - [Whoowns](#whoowns)
  - [Hooks](#hooks)
    - [`check-build-file-without-extensions`](#check-build-file-without-extensions)
    - [`check-snake-case`](#check-snake-case)
    - [`check-cpp-and-cu-unit-test-naming-pattern`](#check-cpp-and-cu-unit-test-naming-pattern)
    - [`check-no-dashes`](#check-no-dashes)
    - [`check-sys-path-append`](#check-sys-path-append)
    - [`check-sys-path-insert`](#check-sys-path-insert)
    - [`go-fmt`](#go-fmt)
    - [`go-imports`](#go-imports)
    - [`go-revive`](#go-revive)
    - [`generate-hook-docs`](#generate-hook-docs)
    - [`check-number-of-lines-count`](#check-number-of-lines-count)
    - [`check-shellscript-set-options`](#check-shellscript-set-options)
    - [`check-jira-reference-in-todo`](#check-jira-reference-in-todo)
    - [`check-load-statement`](#check-load-statement)
    - [`check-non-existing-and-duplicate-excludes`](#check-non-existing-and-duplicate-excludes)
    - [`print-pre-commit-metrics`](#print-pre-commit-metrics)
    - [`sync-vscode-config`](#sync-vscode-config)
    - [`sync-tool-versions`](#sync-tool-versions)
    - [`check-max-one-sentence-per-line`](#check-max-one-sentence-per-line)
    - [`check-ownership`](#check-ownership)
  - [Contributing](#contributing)

<!-- mdformat-toc end -->

## Tools

### Configure VS Code for Bazel

If you want to work with C++ Bazel targets in VS Code, you can use `configure-vscode-for-bazel` to generate a VS Code configuration.
This tool supports generating:

- `.vscode/launch.json` and `tasks.json` files that contain selected targets for debugging and compiling in VS Code and
- a `compile_commands.json` file using [bazel-compile-commands-extractor](https://github.com/hedronvision/bazel-compile-commands-extractor) for selected targets.

To generate these for a defined set of targets, run

```shell
configure-vscode-for-bazel //path/to/your/target/...
```

This will be forwarded to a `bazel query` listing all `cc_binary` and `cc_test` targets.
Then, when you go to `VSCode` -> `Run and Debug (Ctrl+Shift+D)` you'll be able to select an executable.
By pressing `▶ Start Debugging (F5)`, you'll trigger a bazel build command and start debugging the executable.
The latter is provided by `C/C++` Microsoft extension.

Make sure you compile with debug symbols (`--compilation_mode=dbg`) enabled.
You can pass your Bazel flags to this tool with `--additional-debug-arg`.

In addition, a `.vscode/BUILD.bazel` file will be created and `bazel-compile-commands-**extractor**` run to create a `compile_commands.json` in the workspace root.
See [the usage documentation](https://github.com/hedronvision/bazel-compile-commands-extractor?tab=readme-ov-file#usage) for more information.

### Whoowns

`whoowns` is a tool to print the GitHub codeowner of a folder or file by parsing the `.github/CODEOWNERS` file.
With this tool, you can easily find out who is responsible for a specific part of the codebase from the terminal.
To find the owners of a file or folder, run

```shell
whoowns path/to/your/file/or/folder

# example output
# path/to/your/file/or/folder -> @owner1
```

Specify the `--level N` to see the owners of child items in the N-th directory level below your provided folder.

## Hooks

<!-- hooks-doc start -->

### `check-build-file-without-extensions`

Check that `BUILD` files have a `.bazel` ending. `BUILD.bazel` file is the recommended way to name these files.

### `check-snake-case`

Check that all source code files are `snake_case`. We don't want to use `camelCase` or `kebab-case` file names.

### `check-cpp-and-cu-unit-test-naming-pattern`

Check that all C++ and Cuda unit test files end with `_test.cpp` or `_test.cu` (no `_tests`)
and that they're under a `/tests/` folder (not `/test/`).

### `check-no-dashes`

Check that markdown filenames do not use dashes

### `check-sys-path-append`

Check that no `sys.path.append` is used in Python code

### `check-sys-path-insert`

Check that no `sys.path.insert` is used in Python code

### `go-fmt`

Format go files

### `go-imports`

Order go imports

### `go-revive`

Run Go Revive linter

### `generate-hook-docs`

Generate markdown documentation from the hook descriptions in `.pre-commit-hooks.yaml` into the `README.md`. Docs are generated between `hooks-doc start` and `hooks-doc end` markdown comment blocks.

### `check-number-of-lines-count`

Check that number of lines in scripts do not exceed max-lines. Use `--max-lines=<number>` to set the maximum number of lines. Default is 50 for shell scripts.

### `check-shellscript-set-options`

Check if options are set with `set -euxo pipefail`. Use `# nolint(set_options)` to ignore this check.

### `check-jira-reference-in-todo`

Check that all TODO comments follow the same pattern and link a Jira ticket: `TODO(ABC-1234):`.

### `check-load-statement`

Check that a rule is loaded from a specific rule set.

Use `--rule-path` to set the rule set and `--rule-name` to set the rule name.
Example args in the pre-commit config: `args: [--rule-path=@rules_python//python:defs.bzl, --rule-name=py_test]`
Both arguments are required.
Make sure you't put any ticks around the rule path and rule name.
This hook can be used multiple times to check different rules.

### `check-non-existing-and-duplicate-excludes`

Check for non existing and duplicate paths in `.pre-commit-config.yaml`.

Background: In a big codebase, the exclude lists can be quite long and it's easy to make a typo or forget to remove an entry when it's no longer needed.
This hook helps you to maintain a clean and up to date exclude list.

### `print-pre-commit-metrics`

Count the number of excludes in `.pre-commit-config.yaml` and print them in json format.
Use `--output-file` to also write the metrics to a file in json format.
Paths are relative to the root of the repository.

On large projects this can help to collect metrics over time for how many files are excluded from pre-commit.

### `sync-vscode-config`

Sync VSCode settings and extensions from `devcontainer.json` to `.vscode` folder.
`devcontainer.json` will be now your source of truth.
Entries defined in `settings.json` and `extensions.json` which don't exist in `devcontainer.json` will be left as is.

If `settings.json` and `extensions.json` are ignored in Git, consider running the hook in `post-checkout` and `post-merge` stages by overwriting the `stages` config.
In this case, define your `default_install_hook_types` in the pre-commit config and set `always_run: true` for this hook.

### `sync-tool-versions`

Sync tool versions across files based on `.versions.yaml`.
Each version entry defines a `name`, a `version`, and a list of `entries` containing
a file `path` and a regex `pattern` with a single capture group for the version.
You can also use `THE_VERSION` in the pattern as a placeholder for that capture group
(defaults to SemVer with an optional leading `v`).
Use `version_override` on an entry to replace with a different value than the sync `version`.
If you need prefixes like `py314`, use an explicit capture group instead of `THE_VERSION`.

Example `.versions.yaml`:

```yaml
name: tool-versions
sync_versions:
  - name: rust
    version: 1.91.0
    entries:
      - path: MODULE.bazel
        pattern: RUST_VERSION\s*=\s*"THE_VERSION"
      - path: .pre-commit-config.yaml
        pattern: rust:\s*([0-9.]+)
  - name: python
    version: 3.14
    entries:
      - path: .python-version
        pattern: ([0-9]+\.[0-9]+)
      - path: pyproject.toml
        pattern: target-version\s*=\s*\"py([0-9]+)\"
        version_override: '314'
```

### `check-max-one-sentence-per-line`

Check that each line in markdown files contains at most one sentence.
This makes diffs easier to read and avoids merge conflicts.
Sentences are split on `.`, `!`, or `?` followed by a space and a capital letter.

### `check-ownership`

Check if all folders in the `CODEOWNERS` file exist, there are no duplicates, and it has acceptable codeowners.

What is an acceptable codeowner? We want to make sure that every folder has a codeowner other than the team that should exclusively own the CODEOWNERS file.
For this, we define a `CODEOWNERS_OWNER` using the `--codeowners-owner` argument. Your `CODEOWNERS` file should look as follows:

```shell
* CODEOWNERS_OWNER

# Here goes all your CODEOWNERS file content overriding the wildcard owner

# leave this at the bottom to have highest ownership priority
/.github/CODEOWNERS CODEOWNERS_OWNER
```

If the hook detects `CODEOWNERS_OWNER` owns anything else than `.github/CODEOWNERS` it will fail to make sure every file added has an acceptable codeowner.

<!-- hooks-doc end -->

## Contributing

Please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file for information on how to contribute to this project.
