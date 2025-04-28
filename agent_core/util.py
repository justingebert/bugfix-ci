import os, pathlib, subprocess

def print_dir_tree():
    print("\n== File tree ==")
    paths = [pathlib.Path("/agent"), pathlib.Path("/workspace")]
    for p in paths:
        print(f"\n*** {p} ***")
        if subprocess.call(["sh", "-c", f"command -v tree >/dev/null"]) == 0:
            subprocess.run(["tree", "-L", "2", str(p)], check=False)