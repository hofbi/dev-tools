# Whoowns

<!-- rumdl-disable MD013 -->
[![PyPI](https://img.shields.io/pypi/v/whoowns)](https://pypi.org/project/whoowns/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/whoowns)](https://pypi.org/project/whoowns/)
[![PyPI - License](https://img.shields.io/pypi/l/whoowns)](https://pypi.org/project/whoowns/)
<!-- rumdl-enable MD013 -->

`whoowns` is a tool to print the GitHub codeowner of a folder or file by parsing the `CODEOWNERS` file.
With this tool, you can easily find out who is responsible for a specific part of the codebase from the terminal.
To find the owners of a file or folder, run

```shell
uvx whoowns path/to/your/file/or/folder

# example output
# path/to/your/file/or/folder -> @owner1
```

Specify the `--level N` to see the owners of child items in the N-th directory level below your provided folder.

Currently, this supports `CODEOWNERS` file format for GitHub, GitLab, and Bitbucket.
See their docs for more details on where to place the `CODEOWNERS` file.

- GitHub: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners#codeowners-file-location>
- GitLab: <https://docs.gitlab.com/user/project/codeowners/#codeowners-file>
- Bitbucket: <https://support.atlassian.com/bitbucket-cloud/docs/set-up-and-use-code-owners/>
