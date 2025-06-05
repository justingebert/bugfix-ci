import json
import os
import re
from pathlib import Path
import logging

from google import genai
from google.genai import types
from agent_core.stage import Stage
from agent_core.tools.local_repo_tools import find_file, print_dir_tree, get_local_workspace, get_repo_tree

TITLE_RE = re.compile(r"Problem in (\S+)")


class Localize(Stage):
    name = "localize"

    def run(self, ctx):

        workdir = ctx.get("cfg").get("workdir")

        source_files = self._find_files_with_llm(ctx)
        # Fall back to regex-based extraction if LLM approach fails
        if not source_files:
            logging.info(f"[{self.name}] LLM-based localization failed, falling back to regex-based approach")
            match = TITLE_RE.search(ctx["bug"]["title"])
            if not match:
                raise RuntimeError(f"[{self.name}] cannot parse filename from title")

            base_name = match.group(1)
            search_path = Path(get_local_workspace()) / workdir if workdir else Path(get_local_workspace())
            logging.info(f"Searching for {base_name} in {search_path}")

            src_path = find_file(base_name, exts=(".py",), root=search_path)
            if not src_path:
                raise RuntimeError(f"[{self.name}] {base_name}.py not found in repo")

            logging.info(f"[{self.name}] found {base_name}.py in {src_path}")
            source_files = [str(src_path)]

        ctx["source_files"] = source_files

        original_code = {}
        for src_path in source_files:
            with open(src_path, 'r') as f:
                file_content = f.read()
                original_code[src_path] = file_content

        ctx["original_code"] = original_code

        logging.info(f"[{self.name}] Identified source files: {source_files}")
        return ctx

    def _find_files_with_llm(self, ctx):
        """Use Google's Gemini model to identify relevant files for the issue."""
        workdir = ctx.get("cfg").get("workdir", "")
        repo_path = Path(get_local_workspace())
        search_path = repo_path / workdir if workdir else repo_path

        repo_files = get_repo_tree(search_path)

        issue = ctx["bug"]
        prompt = f"""Given the following GitHub issue and repository structure, identify the file(s) that need to be modified to fix the issue.

            Issue #{issue['number']}: {issue['title']}
            Description: {issue.get('body', 'No description provided')}

            Repository files:
            {json.dumps(repo_files, indent=2)}

            Return a JSON array containing ONLY the paths of files that need to be modified to fix this issue.
            Example: ["path/to/file1.py", "path/to/file2.py"]
        """

        try:
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(
                    system_instruction="You are a bug localization system. Look at the issue description and return ONLY the exact file paths that need to be modified."),
                contents=prompt,
            )

            raw_response = response.text
            logging.info(f"[{self.name}] LLM response: {raw_response}")

            json_match = re.search(r'\[\s*"[^"]*"(?:\s*,\s*"[^"]*")*\s*\]', raw_response)
            if json_match:
                file_paths = json.loads(json_match.group(0))
                # Convert to absolute paths
                abs_paths = [str(search_path / path) for path in file_paths]
                return abs_paths
            else:
                logging.warning(f"[{self.name}] Could not parse file paths from LLM response")
                return []

        except Exception as e:
            logging.error(f"[{self.name}] Error querying LLM: {str(e)}")
            return []
