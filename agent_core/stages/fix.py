import os
import pathlib
import logging
import re
from typing import Dict, List, Tuple

from agent_core.stage import Stage, ResultStatus
from google import genai
from google.genai import types
from agent_core.tools.file_tools import clean_code_from_llm_response, load_source_files


class Fix(Stage):
    name = "fix"
    
    FILE_DELIMITER_PATTERN = r'^=== File: (.+?) ===$'

    def run(self, context):
        source_files = context.get("files", {}).get("source_files", [])
        if not source_files:
            raise RuntimeError(f"[{self.name}] No source files found in context for issue #{context['bug']['number']}")

        files_content = load_source_files(source_files)

        if not files_content:
            raise RuntimeError(f"[{self.name}] No readable source files found for issue #{context['bug']['number']}")

        prompt = self._build_prompt(files_content, context.get("previous_attempt_feedback", ""))
        raw_response = self._call_llm(prompt)
        
        fixed_files = self._parse_and_write_files(raw_response, files_content, source_files)
        fixed_files_content = load_source_files(fixed_files)
        context["files"]["fixed_files"] = fixed_files
        logging.info(f"[{self.name}] Successfully edited {len(fixed_files)} files")
        self.set_result(ResultStatus.SUCCESS, "Successfully fixed files", {"fixed_files": fixed_files, "files_content": fixed_files_content})

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

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt and return the response."""
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction="You are part of an automated bug-fixing system. Please return the complete, corrected raw source files for each file that needs changes, never use any markdown formatting. Follow the exact format requested."),
            contents=prompt,
        )
        logging.info(f"[{self.name}] LLM response length: {len(response.text)} characters")
        return response.text

    def _parse_llm_response(self, raw_response: str) -> List[Tuple[str, str]]:
        """Parse LLM response and extract file changes as (filepath, content) tuples."""
        file_changes = []
        lines = raw_response.split('\n')
        current_file = None
        current_content = []

        for line in lines:
            # Check if this line is a file delimiter
            match = re.match(self.FILE_DELIMITER_PATTERN, line.strip())
            if match:
                # Save previous file if exists
                if current_file and current_content:
                    content = '\n'.join(current_content).strip()
                    if content and content != "NO CHANGES NEEDED":
                        file_changes.append((current_file, content))

                # Start new file
                current_file = match.group(1).strip()
                current_content = []
            else:
                if current_file:
                    current_content.append(line)

        # Handle the last file
        if current_file and current_content:
            content = '\n'.join(current_content).strip()
            if content and content != "NO CHANGES NEEDED":
                file_changes.append((current_file, content))

        return file_changes

    def _write_file_changes(self, file_changes: List[Tuple[str, str]], files_content: Dict[str, str]) -> List[str]:
        """Write the parsed file changes to disk and return list of modified files."""
        fixed_files = []
        
        for file_path, new_content in file_changes:
            try:
                cleaned_code = clean_code_from_llm_response(new_content)
                
                path_obj = pathlib.Path(file_path)
                path_obj.write_text(cleaned_code)
                fixed_files.append(str(file_path))
                logging.info(f"[{self.name}] Updated file: {file_path}")
            except Exception as e:
                logging.error(f"[{self.name}] Error writing to file {file_path}: {e}")
        
        return fixed_files

    def _parse_and_write_files(self, raw_response: str, files_content: Dict[str, str], source_files: List[str]) -> List[str]:
        """Parse LLM response and write changes to files."""
        file_changes = self._parse_llm_response(raw_response)
        
        if not file_changes:
            logging.warning(f"[{self.name}] No files were parsed from LLM response")
            logging.debug(f"[{self.name}] Raw response: {raw_response[:500]}...")
            return []
        
        return self._write_file_changes(file_changes, files_content)
