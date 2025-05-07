import subprocess
from agent_core.stage import Stage

class Apply(Stage):
    name = "apply"

    def run(self, ctx):
        print(f"[{self.name}] Committing and pushing changes")

        bug = ctx.get("bug")
        if not bug:
            print(f"[{self.name}] No bug information found. Skipping apply.")
            return ctx

        issue_number = bug.number
        branch_name = f"{issue_number}-fix"

        fixed_files = ctx.get("fixed_files", [])
        if not fixed_files:
            print(f"[{self.name}] No fixed files found to commit.")
            return ctx

        try:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)
            print(f"[{self.name}] Created and checked out branch: {branch_name}")

            for file_path in fixed_files:
                subprocess.run(["git", "add", file_path], check=True, capture_output=True)

            commit_msg = f"Fix issue #{issue_number}: {bug.title}"
            result = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)

            if result.returncode != 0:
                print(f"[{self.name}] Git commit failed: {result.stderr}")
                ctx["apply_results"] = {"status": "failure", "message": result.stderr}
                return ctx

            push_result = subprocess.run(["git", "push", "origin", branch_name], capture_output=True, text=True)

            if push_result.returncode != 0:
                print(f"[{self.name}] Git push failed: {push_result.stderr}")
                ctx["apply_results"] = {"status": "failure", "message": push_result.stderr}
                return ctx

            print(f"[{self.name}] Successfully pushed changes to branch {branch_name}")
            ctx["apply_results"] = {
                "status": "success",
                "branch": branch_name,
                "commit_message": commit_msg
            }

        except Exception as e:
            print(f"[{self.name}] Error applying changes: {str(e)}")
            ctx["apply_results"] = {"status": "failure", "message": str(e)}

        return ctx