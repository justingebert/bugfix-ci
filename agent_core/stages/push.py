import logging
import os
import git
from agent_core.stage import Stage
from agent_core.util.util import get_local_workspace


class Push(Stage):
    name = "push"

    def run(self, ctx):
        """Push committed changes to remote repository."""
        logging.info(f"[{self.name}] Pushing changes to remote")

        apply_results = ctx.get("apply_results", {})
        if apply_results.get("status") != "success":
            logging.warning(f"[{self.name}] Previous apply stage was not successful, skipping push")
            return ctx

        branch_name = ctx.get("branch")
        if not branch_name:
            logging.error(f"[{self.name}] No branch name found in context")
            ctx["push_results"] = {"status": "failure", "message": "No branch name available"}
            return ctx

        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            logging.warning(f"[{self.name}] GITHUB_TOKEN not set - changes committed but not pushed")
            ctx["push_results"] = {"status": "warning", "message": "GitHub token not provided"}
            return ctx

        try:
            repo_path = get_local_workspace()
            repo = git.Repo(repo_path)

            origin = repo.remote("origin")
            original_url = next(origin.urls)

            try:
                if original_url.startswith("https://"):
                    auth_url = original_url.replace("https://", f"https://x-access-token:{github_token}@")

                    origin.set_url(auth_url)

                push_info = origin.push(branch_name)

                if push_info[0].flags & push_info[0].ERROR:
                    error_msg = f"Push failed: {push_info[0].summary}"
                    logging.error(f"[{self.name}] {error_msg}")
                    ctx["push_results"] = {"status": "failure", "message": error_msg}
                else:
                    logging.info(f"[{self.name}] Successfully pushed to {branch_name}")
                    ctx["push_results"] = {
                        "status": "success",
                        "branch": branch_name,
                        "remote": original_url
                    }
            finally:
                if original_url.startswith("https://"):
                    origin.set_url(original_url)

            return ctx

        except git.GitCommandError as e:
            logging.error(f"[{self.name}] Git error: {str(e)}")
            ctx["push_results"] = {"status": "failure", "message": str(e)}
            return ctx
        except Exception as e:
            logging.error(f"[{self.name}] Error pushing changes: {str(e)}")
            ctx["push_results"] = {"status": "failure", "message": str(e)}
            return ctx