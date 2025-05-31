import logging
from agent_core.stage import Stage
from agent_core.tools.local_repo_tools import prepare_issue_branch as prepare_branch_func


class Prepare(Stage):
    name = "prepare"

    def run(self, ctx):
        issue_number = ctx["bug"]["number"]
        success, branch_name = prepare_branch_func(issue_number, ctx)

        if not success:
            raise RuntimeError(f"[{self.name}] Failed to prepare branch for issue #{issue_number}")

        ctx["branch"] = branch_name
        logging.info(f"[{self.name}] Successfully prepared branch: {branch_name}")
        return ctx