import pathlib
import logging
import re
from typing import Dict, List, Tuple

from apr_core.stages.stage import Stage, ResultStatus
from apr_core.tools.file_tools import clean_code_from_llm_response, find_files


class Fix(Stage):
    name = "fix"

    FILE_DELIMITER_PATTERN = r'^=== File: (.+?) ===$'

    def run(self, context):
        source_files = context.get("files", {}).get("source_files", [])
        if not source_files:
            raise RuntimeError(f"[{self.name}] No source files found in context for issue #{context['bug']['number']}")

        files_content = find_files(source_files)

        if not files_content:
            raise RuntimeError(f"[{self.name}] No readable source files found for issue #{context['bug']['number']}")

        system_instruction = "You are part of an automated bug-fixing system. Please return the complete, corrected raw source files for each file that needs changes, never use any markdown formatting. Follow the exact format requested."
        prompt = self._build_prompt(files_content, context.get("previous_attempt_feedback", ""))
        raw_response, tokens = self.llm.generate(prompt, system_instruction)

        fixed_files = self._parse_and_write_files(raw_response, files_content, source_files)
        fixed_files_content = find_files(fixed_files)
        context["files"]["fixed_files"] = fixed_files
        logging.info(f"[{self.name}] Successfully edited {len(fixed_files)} files")
        self.set_result(ResultStatus.SUCCESS, "Successfully fixed files",
                        {"fixed_files": fixed_files, "files_content": fixed_files_content, "tokens": tokens, "raw_response": raw_response})

        return context

    def _build_prompt(self, files_content: Dict[str, str], previous_feedback: str = "") -> str:
        """Build the prompt for the LLM with all files and context."""
        files_text = ""
        for file_path, content in files_content.items():
            files_text += f"\n\n=== File: {file_path} ===\n{content}"

        base_prompt = f"""
The following Python code files have a bug. Please fix the bug across all files as needed.

{files_text}

Please provide the complete, corrected source files. If a file doesn't need changes, you can indicate that.
For each file that needs changes, provide the complete corrected file content.
Format your response as:

=== File: [filepath] ===
[complete file content or "NO CHANGES NEEDED"]

=== File: [filepath] ===
[complete file content or "NO CHANGES NEEDED"]
"""

        if previous_feedback:
            return f"""
The following Python code files have a bug. You tried to fix it before and the attempts context is attached. Please fix the bug across all files as needed.

{files_text}

Previous attempt feedback:
{previous_feedback}

Please analyze what went wrong with your previous fix and provide a working solution.
Provide the complete, corrected source files. If a file doesn't need changes, you can indicate that.
Format your response as:

=== File: [filepath] ===
[complete file content or "NO CHANGES NEEDED"]

=== File: [filepath] ===
[complete file content or "NO CHANGES NEEDED"]
"""
        return base_prompt

    def _parse_llm_response(self, raw_response: str) -> List[Tuple[str, str]]:
        """Parse LLM response and extract file changes as (filepath, content) tuples."""
        file_changes = []

        # Split by file delimiter, capturing the file path
        parts = re.split(self.FILE_DELIMITER_PATTERN, raw_response, flags=re.MULTILINE)

        if len(parts) < 3:
            return []

        # Process each file (skip index 0 which is content before first delimiter)
        for i in range(1, len(parts), 2):
            if i + 1 >= len(parts):
                break

            file_path = parts[i].strip()
            content = parts[i + 1].strip()

            # Clean up common LLM footers
            content = self._clean_llm_footers(content)

            file_changes.append((file_path, content))

        return file_changes

    def _clean_llm_footers(self, content: str) -> str:
        """Remove common LLM-generated footers from code content."""
        # Patterns for various footer messages (case insensitive)
        footer_patterns = [
            r'\s*===?\s*(end of file).*$',
            r'\s*===?\s*(end|done|finished).*$'
        ]

        for pattern in footer_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        return content.strip()

    def _write_file_changes(self, file_changes: List[Tuple[str, str]], files_content: Dict[str, str]) -> List[str]:
        """Write the parsed file changes to disk and return list of modified files."""
        fixed_files: List[str] = []

        for file_path, new_content in file_changes:
            try:
                # Check if LLM indicated no changes needed (case insensitive)
                if re.match(r'^\s*no changes? needed?\s*$', new_content, re.IGNORECASE):
                    # Use original file
                    logging.info(f"[{self.name}] Preserved original file: {file_path}")
                    continue

                cleaned_code = clean_code_from_llm_response(new_content)

                path_obj = pathlib.Path(file_path)
                path_obj.write_text(cleaned_code)
                fixed_files.append(str(file_path))
                logging.info(f"[{self.name}] Updated file: {file_path}")
            except Exception as e:
                logging.error(f"[{self.name}] Error writing to file {file_path}: {e}")

        return fixed_files

    def _parse_and_write_files(self, raw_response: str, files_content: Dict[str, str], source_files: List[str]) -> List[
        str]:
        """Parse LLM response and write changes to files."""
        file_changes = self._parse_llm_response(raw_response)

        if not file_changes:
            logging.warning(f"[{self.name}] No files were parsed from LLM response")
            logging.debug(f"[{self.name}] Raw response: {raw_response[:500]}...")
            return []

        return self._write_file_changes(file_changes, files_content)
