import pathlib, re
import logging
from agent_core.cli import local_work_space
from agent_core.stage import Stage
from agent_core.tools.repo_tools import find_file, print_dir_tree

TITLE_RE = re.compile(r"Problem in (\S+)")

class Localize(Stage):
    name = "localize"
    def run(self, ctx):

        workdir = ctx.get("cfg").get("workdir")
        # paths_to_print = None
        # if workdir:
        #     workdir_path = (pathlib.Path(local_work_space) / workdir).resolve()
        #     paths_to_print = [workdir_path]
        # else:
        #     print("No custom workdir specified. Printing default trees for /workspace.")
        #
        # print_dir_tree(paths_to_print)

        match = TITLE_RE.search(ctx["bug"].title)
        if not match:
            raise RuntimeError(f"[{self.name}] cannot parse filename from title")

        base_name = match.group(1)
        src_path = find_file(base_name, exts=(".py",), root=(pathlib.Path(local_work_space) / workdir).resolve())
        if not src_path:
            raise RuntimeError(f"[{self.name}] {base_name}.py not found in repo")

        logging.info(f"[{self.name}] found {base_name}.py in {src_path}")
        ctx["source_files"] = [str(src_path)]

        with open(src_path, 'r') as f:
            ctx["original_code"] = f.read()

        logging.info(f"[{self.name}] {ctx}")
        return ctx