import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Iterable

import git

from apr_core.util.util import get_local_workspace


def checkout_branch(name, prefix="" ):
    """
    Prepare a branch for fixing a specific issue.
    Creates a new branch if it doesn't exist, or checks out existing branch.
    """
    try:
        branch_name = f"{prefix}{name}"

        repo_path = get_local_workspace()
        repo = git.Repo(repo_path)

        existing_branches = [b.name for b in repo.branches]

        if branch_name in existing_branches:
            logging.info(f"Branch {branch_name} already exists, checking it out")
            repo.git.checkout(branch_name)
        else:
            logging.info(f"Creating new branch {branch_name}")
            repo.git.checkout("-b", branch_name)

        return branch_name
    except Exception as e:
        logging.error(f"Error preparing branch: {str(e)}")
        return None


def get_repo_tree(root_path, ignore_dirs=None):
    """
    Generate a list of file paths in the repository.
    """
    if ignore_dirs is None:
        ignore_dirs = ['.git', '__pycache__', 'venv', '.venv', 'node_modules']

    file_paths = []

    for root, dirs, files in os.walk(root_path):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for file in files:
            # Only include source code files
            if file.endswith(('.py', '.java', '.js', '.ts', '.html', '.css')):
                rel_path = os.path.relpath(os.path.join(root, file), root_path)
                file_paths.append(rel_path)

    return sorted(file_paths)

def find_file(name: str, extension: Iterable[str] = (".py",), root: Optional[Path] = None) -> Optional[Path]:
    if root is None:
        root = Path(get_local_workspace())

    logging.info(f"Finding file: name={name}, extension={extension}")
    logging.info(f"Search root: {root} (absolute: {root.absolute()})")
    logging.info(f"Root exists: {root.exists()}")

    if root.exists():
        logging.info("Files in search directory:")
        for i, item in enumerate(root.glob('*')):
            logging.info(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
            if i > 20:  # Limit output
                logging.info("  ... (more files)")
                break


    target_names = {name} | {f"{name}{ext}" for ext in extension}
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


def reset_files(files: Optional[Iterable[str]] = None, branch: str = None) -> bool:
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

        if branch:
            repo.git.checkout(branch)
            logging.info("Successfully reset to main branch")
            
    except git.GitCommandError as e:
        raise RuntimeError(f"Git error resetting to main branch: {e}")
    except Exception as e:
        raise RuntimeError(f"Error resetting to main branch: {str(e)}")

#TODO get repo structure with files as keys and functions/classes as values
def get_repo_structure(repo_path: Optional[str] = None) -> dict:
    """
    Get the structure of the repository.
    Returns a dictionary with file paths and their types.
    """

    structure = {}

    logging.info(f"Repository structure: {structure}")
    return structure


def apply_changes_to_branch(branch_name: str, fixed_files: list[str], diff_dir=None, commit_info:str = None) -> Optional[str]:
    """
    Apply changes to the specified branch and returns diff file.
    """
    try:
        repo_path = get_local_workspace()
        repo = git.Repo(repo_path)

        if repo.active_branch.name != branch_name:
            logging.info(f"Switching to branch {branch_name}")
            repo.git.checkout(branch_name)

        for file in fixed_files:
            file_path = Path(repo_path) / file
            if file_path.exists():
                repo.git.add(str(file_path))
                logging.info(f"Added file {file} to staging area")
            else:
                logging.warning(f"File {file} does not exist, skipping add")

        diff = repo.git.diff("--staged")
        if not diff:
            logging.warning("No changes detected in staged files")
            return None

        staged_files = repo.git.diff("--name-only", "--staged").splitlines()
        commit_msg = f"Fix issue {commit_info}"
        repo.git.commit("-m", commit_msg)
        logging.info(f"{len(staged_files)} files with changes committed to branch {branch_name}")


        if diff_dir:
            diff_file = Path(str(diff_dir)) / f"issue_{commit_info}_diff.patch"
            with open(diff_file, 'w') as f:
                f.write(diff)

            logging.info(f"Generated diff saved to {diff_file}")
            return str(diff_file)


    except git.GitCommandError as e:
        raise RuntimeError(f"Git error applying changes: {e}")
    except Exception as e:
        raise RuntimeError(f"Error applying changes: {str(e)}")

def push_changes(branch_name):
    """
    Push committed changes to remote repository.
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN not set - changes committed but not pushed")

    try:
        repo_path = get_local_workspace()
        repo = git.Repo(repo_path)

        origin = repo.remote("origin")
        original_url = next(origin.urls)

        if original_url.startswith("https://"):
            auth_url = original_url.replace("https://", f"https://x-access-token:{github_token}@")

            origin.set_url(auth_url)

            push_info = origin.push(branch_name)

            if push_info[0].flags & push_info[0].ERROR:
                raise RuntimeError( f"Push failed: {push_info[0].summary}")
            else:
                logging.info("Push successfull")

    except git.GitCommandError as e:
        raise RuntimeError(f"Git error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error pushing changes: {str(e)}")
    finally:
        if original_url.startswith("https://"):
            origin.set_url(original_url)