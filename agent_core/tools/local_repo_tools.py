from pathlib import Path
import subprocess
from typing import Optional, Iterable
import logging
import os
import git

from agent_core.util.util import get_local_workspace


def prepare_issue_branch(issue_number, ctx):
    """
    Prepare a branch for fixing a specific issue.
    Creates a new branch if it doesn't exist, or checks out existing branch.
    """
    try:

        branch_prefix = ctx.get("cfg", {}).get("branch_prefix", "fix-issue-")
        branch_name = f"{branch_prefix}{issue_number}"

        repo_path = get_local_workspace()
        repo = git.Repo(repo_path)

        existing_branches = [b.name for b in repo.branches]

        if branch_name in existing_branches:
            logging.info(f"Branch {branch_name} already exists, checking it out")
            repo.git.checkout(branch_name)
        else:
            logging.info(f"Creating new branch {branch_name}")
            repo.git.checkout("-b", branch_name)

        return True, branch_name
    except git.GitCommandError as e:
        logging.error(f"Git error preparing branch: {e}")
        return False, None
    except Exception as e:
        logging.error(f"Error preparing branch: {str(e)}")
        return False, None

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
        repo_path = get_local_workspace()
        repo = git.Repo(repo_path)
        logging.info("Resetting to main branch")

        # Reset just the edited files
        if files:
            for file in files:
                file_path = Path(file)
                if file_path.exists():
                    repo.git.checkout('--', file)
                    logging.info(f"Reset {file} to main branch")
                else:
                    logging.warning(f"File {file} does not exist, skipping reset")

        repo.git.checkout('main')
        logging.info("Successfully reset to main branch")
        return True
    except git.GitCommandError as e:
        logging.error(f"Git error resetting to main branch: {e}")
        return False
    except Exception as e:
        logging.error(f"Error resetting to main branch: {str(e)}")
        return False
