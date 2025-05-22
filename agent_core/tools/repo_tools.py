import pathlib
from pathlib import Path
import subprocess
from typing import Optional, Iterable
import logging
import os

#TODO clean up
def get_local_workspace():
    """Get the local workspace path without circular imports"""
    return "workspace" if os.getenv("ENV") == "dev-deployed" else ""

def print_dir_tree(paths=None):
    """Prints the directory tree for the given paths, or defaults."""
    logging.info("\n== File tree ==")
    if paths is None:
        paths = [pathlib.Path("/workspace")]

    for p in paths:
        logging.info(f"\n*** {p} ***")
        if subprocess.call(["sh", "-c", "command -v tree >/dev/null"]) == 0:
            subprocess.run(["tree", "-L", "2", str(p)], check=False)
        else:
            logging.info(f"[warn] 'tree' command not found. Cannot print directory tree for {p}.")


def find_file(name: str, exts: Iterable[str] = (".py",), root: Optional[Path] = None) -> Optional[Path]:
    if root is None:
        local_work_space = get_local_workspace()
        root = Path(local_work_space)

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


def reset_to_main():
    """Reset git to main branch and clean working directory"""
    try:
        os.chdir('/workspace')
        logging.info("Resetting to main branch")

        #subprocess.run(["git", "reset", "--hard"], check=True, capture_output=True)

        subprocess.run(["git", "checkout", "main"], check=True, capture_output=True)

        logging.info("Successfully reset to main branch")
        return True
    except Exception as e:
        logging.error(f"Error resetting to main branch: {str(e)}")
        return False
