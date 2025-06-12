from agent_core.stage import Stage
from agent_core.tools.github_tools import get_repo, add_issue_label
import logging

class Report(Stage):
    name = "report"

    def run(self, context):
        logging.info(f"[{self.name}] Creating PR for the bug fix")

        bug = context.get("bug")
        if not bug:
            logging.info(f"[{self.name}] No bug information found. Skipping report.")
            return context

        apply_results = context.get("apply_results", {})
        if apply_results.get("status") != "success":
            logging.info(f"[{self.name}] Apply stage was not successful. Skipping PR creation.")
            return context

        branch_name = apply_results.get("branch")
        if not branch_name:
            logging.info(f"[{self.name}] Branch name not found in apply_results. Skipping report.")
            context["report_results"] = {
                "status": "failure",
                "message": "Branch name not found after apply stage."
            }
            return context

        issue_number = bug["number"]
        branch_name = apply_results.get("branch", f"{issue_number}-fix")

        try:
            repo = get_repo()
            repo_owner_login = repo.owner.login

            pr_title = f"Fix for issue #{issue_number}: {bug['title']}"

            pr_body = f"fixes #{issue_number}\n\n"
            pr_body += "## Changes\n"

            fixed_files = context.get("fixed_files", [])
            if fixed_files:
                pr_body += "### Modified files:\n"
                for file_path in fixed_files:
                    pr_body += f"- `{file_path}`\n"

            test_results = context.get("test_results", {})
            if test_results:
                pr_body += "\n### Test Results\n"
                pr_body += f"Status: {test_results.get('status', 'Unknown')}\n"

            existing_pr = None
            head_branch_ref = f"{repo_owner_login}:{branch_name}"
            open_pulls = repo.get_pulls(state='open', head=head_branch_ref, base='main')
            if open_pulls.totalCount > 0:
                existing_pr = open_pulls[0]

            if existing_pr:
                logging.info(f"[{self.name}] Found existing PR #{existing_pr.number}. Updating it.")
                existing_pr.edit(title=pr_title, body=pr_body)
                # existing_pr.create_issue_comment("This PR has been automatically updated with the latest fixes.")
                pr = existing_pr
                action = "updated"
                logging.info(f"[{self.name}] Successfully updated PR #{pr.number}: {pr_title}")
            else:
                logging.info(f"[{self.name}] Creating new PR for branch '{branch_name}' into 'main'.")
                pr = repo.create_pull(
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base="main"
                )
                action = "created"
                logging.info(f"[{self.name}] Successfully created PR #{pr.number}: {pr_title}")

            #add label to issue
            fix_submitted_label = context.get("cfg", {}).get("submitted_fix_label")
            add_issue_label(bug["number"], fix_submitted_label)

            context["report_results"] = {
                "status": "success",
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "action": action
            }

        except Exception as e:
            logging.info(f"[{self.name}] Error creating/updating PR: {str(e)}")
            context["report_results"] = {"status": "failure", "message": str(e)}

        return context