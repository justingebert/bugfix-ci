import os, pathlib, subprocess, yaml

def _read_yaml(path: pathlib.Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def print_dir_tree(paths=None):
    """Prints the directory tree for the given paths, or defaults."""
    print("\n== File tree ==")
    if paths is None:
        paths = [pathlib.Path("/workspace")]

    for p in paths:
        print(f"\n*** {p} ***")
        if subprocess.call(["sh", "-c", "command -v tree >/dev/null"]) == 0:
            subprocess.run(["tree", "-L", "2", str(p)], check=False)
        else:
            print(f"[warn] 'tree' command not found. Cannot print directory tree for {p}.")