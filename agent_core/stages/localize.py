import json
import re
from pathlib import Path
import logging

from agent_core.stage import Stage, ResultStatus
from agent_core.tools.file_tools import load_source_files
from agent_core.tools.local_repo_tools import find_file, get_local_workspace, get_repo_tree

TITLE_RE = re.compile(r"Problem in (\S+)")

##TODO continue here with adding source file dict for attempt retry
class Localize(Stage):
    name = "localize"

    def run(self, context):

        source_files, tokens = self._find_files_with_llm(context)

        if not source_files:
            raise RuntimeError(f"[{self.name}] Failed to localize Files for Issue #{context['bug']['number']}")

        context["files"]["source_files"] = source_files
        context["files"]["original_source_files"] = load_source_files(source_files)

        self.set_result(ResultStatus.SUCCESS,
                        f"Identified source files for issue #{context['bug']['number']}: {source_files}",
                        {"source_files": source_files, "tokens": tokens})

        logging.info(f"[{self.name}] Identified source files: {source_files}")
        return context

    def _find_files_with_llm(self, context):
        """Use LLM model to identify relevant files for the issue."""
        workdir = context.get("cfg").get("workdir", "")
        repo_path = Path(get_local_workspace())
        search_path = repo_path / workdir if workdir else repo_path

        repo_files = get_repo_tree(search_path)

        issue = context["bug"]
        prompt = f"""Given the following GitHub issue and repository structure, identify the file(s) that need to be modified to fix the issue.

            Issue #{issue['number']}: {issue['title']}
            Description: {issue.get('body', 'No description provided')}

            Repository files:
            {json.dumps(repo_files, indent=2)}

            Return a JSON array containing ONLY the paths of files that need to be modified to fix this issue.
            Example: ["path/to/file1.py", "path/to/file2.py"]
        """

        system_instruction = "You are a bug localization system. Look at the issue description and return ONLY the exact file paths that need to be modified."

        raw_response, tokens = self.llm.generate(prompt, system_instruction)
        logging.info(f"[{self.name}] LLM response: {raw_response}")

        json_match = re.search(r'\[\s*"[^"]*"(?:\s*,\s*"[^"]*")*\s*\]', raw_response)
        if json_match:
            file_paths = json.loads(json_match.group(0))
            # Convert to absolute paths
            abs_paths = [str(search_path / path) for path in file_paths]
            return abs_paths, tokens
        else:
            logging.warning(f"[{self.name}] Could not parse file paths from LLM response")
            return [], tokens
