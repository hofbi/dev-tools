# configure-vscode-for-bazel

[![PyPI](https://img.shields.io/pypi/v/configure-vscode-for-bazel)](https://pypi.org/project/configure-vscode-for-bazel/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/configure-vscode-for-bazel)](https://pypi.org/project/configure-vscode-for-bazel/)
[![PyPI - License](https://img.shields.io/pypi/l/configure-vscode-for-bazel)](https://pypi.org/project/configure-vscode-for-bazel/)

If you want to work with C++ Bazel targets in VS Code, you can use `configure-vscode-for-bazel` to generate a VS Code configuration.
This tool supports generating:

- `.vscode/launch.json` and `tasks.json` files that contain selected targets for debugging and compiling in VS Code and
- a `compile_commands.json` file using [bazel-compile-commands-extractor](https://github.com/hedronvision/bazel-compile-commands-extractor) for selected targets.

To generate these for a defined set of targets, run

```shell
uvx configure-vscode-for-bazel //path/to/your/target/...
```

This will be forwarded to a `bazel query` listing all `cc_binary` and `cc_test` targets.
Then, when you go to `VSCode` -> `Run and Debug (Ctrl+Shift+D)` you'll be able to select an executable.
By pressing `▶ Start Debugging (F5)`, you'll trigger a bazel build command and start debugging the executable.
The latter is provided by `C/C++` Microsoft extension.

Make sure you compile with debug symbols (`--compilation_mode=dbg`) enabled.
You can pass your Bazel flags to this tool with `--additional-debug-arg`.

In addition, a `.vscode/BUILD.bazel` file will be created and `bazel-compile-commands-**extractor**` run to create a `compile_commands.json` in the workspace root.
See [the usage documentation](https://github.com/hedronvision/bazel-compile-commands-extractor?tab=readme-ov-file#usage) for more information.