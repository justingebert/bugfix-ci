from pathlib import Path
import subprocess
from typing import Optional, Iterable
import logging
import os

from agent_core.util.util import get_local_workspace


def print_dir_tree(paths):
    """Prints the directory tree for the given paths, or defaults."""
    logging.info("\n== File tree ==")

    for p in paths:
        logging.info(f"\n*** {p} ***")
        if subprocess.call(["sh", "-c", "command -v tree >/dev/null"]) == 0:
            subprocess.run(["tree", "-L", "2", str(p)], check=False)
        else:
            logging.info(f"[warn] 'tree' command not found. Cannot print directory tree for {p}.")


def find_file(name: str, exts: Iterable[str] = (".py",), root: Optional[Path] = None) -> Optional[Path]:
    if root is None:
        root = Path(get_local_workspace())

    logging.info(f"Finding file: name={name}, exts={exts}")
    logging.info(f"Search root: {root} (absolute: {root.absolute()})")
    logging.info(f"Root exists: {root.exists()}")

    if root.exists():
        logging.info("Files in search directory:")
        for i, item in enumerate(root.glob('*')):
            logging.info(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
            if i > 20:  # Limit output
                logging.info("  ... (more files)")
                break


    target_names = {name} | {f"{name}{ext}" for ext in exts}
    logging.info(f"Looking for any of: {target_names}")

    files_found = []
    for path in root.rglob("*"):
        if path.is_file():
            files_found.append(str(path))
            if path.name in target_names:
                logging.info(f"Found match: {path}")
                return path.resolve()

    logging.info(f"Search completed. Files found: {len(files_found)}")
    logging.info(f"First 10 files searched: {files_found[:10]}")
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


def reset_to_main(files: Optional[Iterable[str]] = None) -> bool:
    """Reset git to main branch and clean working directory"""
    try:
        os.chdir(get_local_workspace())
        logging.info("Resetting to main branch")
        #reset just the edited files
        for file in files or []:
            if Path(file).exists():
                subprocess.run(["git", "checkout", "--", file], check=True, capture_output=True)
                logging.info(f"Reset {file} to main branch")
            else:
                logging.warning(f"File {file} does not exist, skipping reset")

        #subprocess.run(["git", "reset", "--hard"], check=True, capture_output=True)

        subprocess.run(["git", "checkout", "main"], check=True, capture_output=True)
        logging.info("Successfully reset to main branch")
        return True
    except Exception as e:
        logging.error(f"Error resetting to main branch: {str(e)}")
        return False
