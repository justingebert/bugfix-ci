import logging
from pathlib import Path
import git
from agent_core.stage import Stage
from agent_core.util.util import get_local_workspace

class Apply(Stage):
    name = "apply"

    def run(self, ctx):
        """Commit changes and generate diff."""
        logging.info(f"[{self.name}] Applying changes and generating diff")

        bug = ctx.get("bug")
        if not bug:
            logging.error(f"[{self.name}] No bug information found")
            return ctx

        issue_number = bug["number"]
        branch_name = ctx.get("branch")
        fixed_files = ctx.get("fixed_files", [])

        if not branch_name:
            logging.error(f"[{self.name}] No branch name found in context")
            ctx["apply_results"] = {"status": "failure", "message": "No branch name available"}
            return ctx

        if not fixed_files:
            logging.warning(f"[{self.name}] No fixed files found to commit")
            ctx["apply_results"] = {"status": "failure", "message": "No fixed files to commit"}
            return ctx

        try:
            repo_path = get_local_workspace()
            repo = git.Repo(repo_path)

            current_branch = repo.active_branch.name
            if current_branch != branch_name:
                logging.info(f"[{self.name}] Switching from {current_branch} to {branch_name}")
                repo.git.checkout(branch_name)

            added_files = []
            for file_path in fixed_files:
                file = Path(repo_path) / file_path
                rel_path = file.relative_to(repo_path)

                if file.exists():
                    try:
                        repo.git.add(str(rel_path))
                        added_files.append(str(rel_path))
                        logging.info(f"[{self.name}] Added file: {rel_path}")
                    except git.GitCommandError as e:
                        logging.error(f"[{self.name}] Failed to add file {rel_path}: {str(e)}")
                else:
                    logging.warning(f"[{self.name}] File does not exist: {rel_path}")

            diff = repo.git.diff("--staged")

            if not diff:
                logging.warning(f"[{self.name}] No changes detected in staged files")
                ctx["apply_results"] = {"status": "warning", "message": "No changes detected in staged files"}
                return ctx

            diff_file = Path(str(ctx.get("log_dir"))) / f"issue_{issue_number}_diff.patch"
            with open(diff_file, 'w') as f:
                f.write(diff)

            logging.info(f"[{self.name}] Generated diff saved to {diff_file}")
            ctx["diff_file"] = str(diff_file)

            staged_files = repo.git.diff("--name-only", "--staged").splitlines()
            if staged_files:
                commit_msg = f"Fix issue #{issue_number}: {bug['title']}"
                repo.git.commit("-m", commit_msg)
                logging.info(f"[{self.name}] Changes committed with message: {commit_msg}")
                logging.info(f"[{self.name}] Committed files: {', '.join(staged_files)}")
                ctx["apply_results"] = {
                    "status": "success",
                    "branch": branch_name,
                    "commit_message": commit_msg,
                    "diff_file": str(diff_file),
                    "committed_files": staged_files
                }
            else:
                logging.warning(f"[{self.name}] No changes to commit")
                ctx["apply_results"] = {"status": "warning", "message": "No changes to commit"}

            return ctx

        except git.GitCommandError as e:
            logging.error(f"[{self.name}] Git error: {str(e)}")
            ctx["apply_results"] = {"status": "failure", "message": str(e)}
            return ctx
        except Exception as e:
            logging.error(f"[{self.name}] Error applying changes: {str(e)}")
            ctx["apply_results"] = {"status": "failure", "message": str(e)}
            return ctx