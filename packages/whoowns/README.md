# whoowns

[![PyPI](https://img.shields.io/pypi/v/whoowns)](https://pypi.org/project/whoowns/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/whoowns)](https://pypi.org/project/whoowns/)
[![PyPI - License](https://img.shields.io/pypi/l/whoowns)](https://pypi.org/project/whoowns/)

`whoowns` is a tool to print the GitHub codeowner of a folder or file by parsing the `CODEOWNERS` file.
With this tool, you can easily find out who is responsible for a specific part of the codebase from the terminal.
To find the owners of a file or folder, run

```shell
uvx whoowns path/to/your/file/or/folder

# example output
# path/to/your/file/or/folder -> @owner1
```

Specify the `--level N` to see the owners of child items in the N-th directory level below your provided folder.

Currently, this supports only GitHub's `CODEOWNERS` file format, but support for other formats such as GitLab may be added upon request.
