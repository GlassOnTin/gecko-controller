#!/usr/bin/env python3
import subprocess
import os


def concat_git_files(output_file="all.txt"):
    # Get tracked files respecting .gitignore
    files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()

    # Filter by extension
    extensions = {".py", ".cpp", ".h", ".i", ".txt", ".md", ".html", ".js", ".toml"}
    paths = {"debian"}
    excludes = {"changelog"}

    # Filter files based on extensions, included paths, and excludes
    files = [f for f in files if
             (os.path.splitext(f)[1] in extensions or
              any(f.startswith(path) for path in paths)) and
             not any(f.startswith(exclude) for exclude in excludes)]

    # Write concatenated output
    with open(output_file, "w") as outfile:
        for file in files:
            if os.path.basename(file) == output_file:
                continue
            print(file)
            outfile.write(f"\n//{file}\n")
            with open(file, "r") as infile:
                outfile.write(infile.read())

    print(f"\n=> {output_file}")


if __name__ == "__main__":
    concat_git_files()
