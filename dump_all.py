#!/usr/bin/env python3
import subprocess
import os


def concat_git_files(output_file="all.txt"):
    # Get tracked files respecting .gitignore
    files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()

    # Filter by extension
    #extensions = {".sh", ".py", ".cpp", ".h", ".i", ".txt", ".md", ".html", ".js", ".jsx", ".toml"}
    paths = {"./", "tests/", "gecko_controller/"}
    excludes = {"dump_all.py", ".github", "changelog", "gitignore", "jpg", "fonts", "license"}

    # Filter files based on extensions, included paths, and excludes
    files = [f for f in files if
             not any(exclude.lower() in f.lower() for exclude in excludes)
             and any(include.lower() in f.lower() for include in paths)]

    # Write concatenated output
    with open(output_file, "w") as outfile:
        for file in files:
            if os.path.basename(file) == output_file:
                continue
            print(file)
            outfile.write(f"\n//{file}\n")
            try:
                with open(file, "r") as infile:
                    outfile.write(infile.read())
            except Exception as e:
                outfile.write(repr(e))

    print(f"\n=> {output_file}")


if __name__ == "__main__":
    concat_git_files()
