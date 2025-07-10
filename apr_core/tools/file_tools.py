import logging
import pathlib
import re
from typing import List

from apr_core.util.util import get_local_workspace


def clean_code_from_llm_response(response_text):
    """Clean markdown formatting from LLM response."""
    # extract code from markdown code blocks
    code_block_pattern = r'```(?:python)?\s*(.*?)\s*```'
    code_blocks = re.findall(code_block_pattern, response_text, re.DOTALL)

    if code_blocks:
        return max(code_blocks, key=len)  # Return the longest code block

    # Remove markdown markers if present
    cleaned = re.sub(r'```(?:python)?\s*', '', response_text)
    cleaned = re.sub(r'```\s*', '', cleaned)

    # If the cleaned text looks valid, use it:
    return cleaned.strip()


def find_files(source_files: List[str]) -> dict[str, str]:
    """
        Load source files and return their content as a dictionary.
        If a file path is not found, it searches the entire repository for a file with the same name.
        """
    files_content = {}
    repo_root = pathlib.Path(get_local_workspace())

    for file_path_str in source_files:
        try:
            path_obj = pathlib.Path(file_path_str)
            # Use absolute path for existence check
            if not path_obj.is_absolute():
                path_obj = repo_root / path_obj

            if path_obj.exists() and path_obj.is_file():
                files_content[str(path_obj)] = path_obj.read_text()
                logging.info(f"Loaded file: {path_obj}")
            else:
                logging.warning(
                    f"File not found at '{file_path_str}'. Searching repository for filename '{path_obj.name}'.")
                # Search for the file in the repository
                found = False
                for potential_match in repo_root.rglob(path_obj.name):
                    if potential_match.is_file():
                        files_content[str(potential_match)] = potential_match.read_text()
                        logging.info(f"Found and loaded file at alternative path: {potential_match}")
                        found = True
                        break  # Stop after finding the first match
                if not found:
                    logging.error(f"Could not find file '{path_obj.name}' anywhere in the repository.")

        except Exception as e:
            logging.error(f"Error reading file {file_path_str}: {e}")

    return files_content