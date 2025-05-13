import subprocess
from agent_core.stage import Stage
import os

class Apply(Stage):
    name = "apply"

    def run(self, ctx):
        logging.info(f"[{self.name}] Committing and pushing changes")

        bug = ctx.get("bug")
        if not bug:
            logging.info(f"[{self.name}] No bug information found. Skipping apply.")
            return ctx

        issue_number = bug.number
        branch_name = f"fix-{issue_number}"

        fixed_files = ctx.get("fixed_files", [])
        if not fixed_files:
            logging.info(f"[{self.name}] No fixed files found to commit.")
            return ctx

        os.chdir('/workspace')
        logging.info(f"[{self.name}] Working directory changed to: {os.getcwd()}")

        try:
            remote_url_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, check=True
            )
            remote_url = remote_url_result.stdout.strip()
            logging.info(f"[{self.name}] Detected remote URL: {remote_url}")

            subprocess.run(["git", "status"], capture_output=True, text=True)
            result = subprocess.run(["git", "branch", "--list", branch_name], capture_output=True, text=True)
            if branch_name in result.stdout:
                logging.info(f"[{self.name}] Branch {branch_name} already exists, checking it out")
                subprocess.run(["git", "checkout", branch_name], check=True, capture_output=True)
            else:
                subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)
                logging.info(f"[{self.name}] Created and checked out branch: {branch_name}")

            for file_path in fixed_files:
                subprocess.run(["git", "add", file_path], check=True, capture_output=True)

            commit_msg = f"Fix issue #{issue_number}: {bug.title}"
            result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)

            if result.returncode != 0:
                logging.info(f"[{self.name}] Git commit failed: {result.stderr}")
                ctx["apply_results"] = {"status": "failure", "message": result.stderr}
                return ctx

            github_token = os.environ.get("GITHUB_TOKEN")
            if not github_token:
                logging.info(f"[{self.name}] Error: GITHUB_TOKEN environment variable not set")
                ctx["apply_results"] = {"status": "failure", "message": "GitHub token not provided"}
                return ctx

            # Modify remote URL to include token for authentication
            original_remote = remote_url
            if remote_url.startswith("https://"):
                auth_remote = remote_url.replace("https://", f"https://x-access-token:{github_token}@")
                subprocess.run(["git", "remote", "set-url", "origin", auth_remote], capture_output=True, check=True)
                logging.info(f"[{self.name}] Configured authentication for push")

            push_result = subprocess.run(["git", "push", "origin", branch_name], capture_output=True, text=True)

            # Reset remote URL to original (for security)
            if remote_url.startswith("https://"):
                subprocess.run(["git", "remote", "set-url", "origin", original_remote], capture_output=True, check=True)

            if push_result.returncode != 0:
                logging.info(f"[{self.name}] Git push failed: {push_result.stderr}")
                ctx["apply_results"] = {"status": "failure", "message": push_result.stderr}
                return ctx

            logging.info(f"[{self.name}] Successfully pushed changes to branch {branch_name}")
            ctx["apply_results"] = {
                "status": "success",
                "branch": branch_name,
                "commit_message": commit_msg
            }

        except Exception as e:
            logging.info(f"[{self.name}] Error applying changes: {str(e)}")
            ctx["apply_results"] = {"status": "failure", "message": str(e)}

        return ctx