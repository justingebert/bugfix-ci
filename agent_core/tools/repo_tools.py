import pathlib
from pathlib import Path
import subprocess
from typing import Optional, Iterable
from agent_core.cli import local_work_space


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

def find_file(name: str, exts: Iterable[str] = (".py",), root: Path = Path(local_work_space)) -> Optional[Path]:
    target_names = {name} | {f"{name}{ext}" for ext in exts}
    for path in root.rglob("*"):
        if path.is_file() and path.name in target_names:
            return path.resolve()
    return None


def run_command(command: list[str], file_path: Path) -> tuple[bool, str, str]:
    """Helper to run a command and capture output."""
    try:
        process = subprocess.run(command + [str(file_path)], capture_output=True, text=True, check=False)
        success = process.returncode == 0
        return success, process.stdout, process.stderr
    except FileNotFoundError:
        return False, "", f"Command not found: {command[0]}"
    except Exception as e:
        return False, "", f"Error running command {' '.join(command)}: {e}"
