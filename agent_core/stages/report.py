from agent_core.stage import Stage
from agent_core.issue_helper import get_repo


class Report(Stage):
    name = "report"

    def run(self, ctx):
        print(f"[{self.name}] Creating PR for the bug fix")

        apply_results = ctx.get("apply_results", {})
        if apply_results.get("status") != "success":
            print(f"[{self.name}] Apply stage was not successful. Skipping PR creation.")
            return ctx

        bug = ctx.get("bug")
        if not bug:
            print(f"[{self.name}] No bug information found. Skipping report.")
            return ctx

        issue_number = bug.number
        branch_name = apply_results.get("branch", f"{issue_number}-fix")

        try:
            repo = get_repo()

            pr_title = f"Fix for issue #{issue_number}: {bug.title}"

            pr_body = f"This PR fixes issue #{issue_number}\n\n"
            pr_body += "## Changes\n"

            fixed_files = ctx.get("fixed_files", [])
            if fixed_files:
                pr_body += "### Modified files:\n"
                for file_path in fixed_files:
                    pr_body += f"- `{file_path}`\n"

            test_results = ctx.get("test_results", {})
            if test_results:
                pr_body += "\n### Test Results\n"
                pr_body += f"Status: {test_results.get('status', 'Unknown')}\n"

            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base="main"
            )

            print(f"[{self.name}] Successfully created PR #{pr.number}: {pr_title}")
            ctx["report_results"] = {
                "status": "success",
                "pr_number": pr.number,
                "pr_url": pr.html_url
            }

        except Exception as e:
            print(f"[{self.name}] Error creating PR: {str(e)}")
            ctx["report_results"] = {"status": "failure", "message": str(e)}

        return ctx