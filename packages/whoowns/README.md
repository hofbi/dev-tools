# whoowns

`whoowns` is a tool to print the GitHub codeowner of a folder or file by parsing the `.github/CODEOWNERS` file.
With this tool, you can easily find out who is responsible for a specific part of the codebase from the terminal.
To find the owners of a file or folder, run

```shell
uvx whoowns path/to/your/file/or/folder

# example output
# path/to/your/file/or/folder -> @owner1
```

Specify the `--level N` to see the owners of child items in the N-th directory level below your provided folder.