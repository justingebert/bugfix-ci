import re
from pathlib import Path
import logging
from agent_core.stage import Stage
from agent_core.tools.local_repo_tools import find_file, print_dir_tree, get_local_workspace

TITLE_RE = re.compile(r"Problem in (\S+)")

class Localize(Stage):
    name = "localize"
    def run(self, ctx):

        workdir = ctx.get("cfg").get("workdir")

        logging.info(f"Current directory structure:")
        paths_to_print = None
        if workdir:
            workdir_path = Path(get_local_workspace()) / workdir
            paths_to_print = [workdir_path]
            logging.info(f"Looking in workdir: {workdir_path}")

        print_dir_tree(paths_to_print)

        match = TITLE_RE.search(ctx["bug"].title)
        if not match:
            raise RuntimeError(f"[{self.name}] cannot parse filename from title")

        base_name = match.group(1)
        search_path = Path(get_local_workspace()) / workdir
        logging.info(f"Searching for {base_name} in {search_path}")

        src_path = find_file(base_name, exts=(".py",), root=search_path)
        if not src_path:
            raise RuntimeError(f"[{self.name}] {base_name}.py not found in repo")

        logging.info(f"[{self.name}] found {base_name}.py in {src_path}")
        ctx["source_files"] = [str(src_path)]

        with open(src_path, 'r') as f:
            ctx["original_code"] = f.read()

        logging.info(f"[{self.name}] {ctx}")
        return ctx