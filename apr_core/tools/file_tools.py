import logging
import pathlib
import re
from typing import List

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


def load_source_files(source_files: List[str]) -> dict[str, str]:
    """Load source files and return their content as a dictionary."""
    files_content = {}
    for file_path in source_files:
        try:
            path_obj = pathlib.Path(file_path)
            if path_obj.exists():
                files_content[file_path] = path_obj.read_text()
                logging.info(f"Loaded file: {file_path}")
            else:
                logging.warning(f"File not found: {file_path}")
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
    return files_content