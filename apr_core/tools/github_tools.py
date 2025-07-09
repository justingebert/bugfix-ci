import logging
import os
import sys

from github import Github, Issue, Repository

def get_repo() -> Repository.Repository:
    token = os.getenv("GITHUB_TOKEN")
    repository  = os.getenv("GITHUB_REPOSITORY")
    if not token or not repository:
        sys.exit("❌  GITHUB_TOKEN and GITHUB_REPOSITORY env vars are required ❌")
    return Github(token).get_repo(repository)

def report_failure(issue_number, message, label):
    repo = get_repo()
    issue = repo.get_issue(int(issue_number))
    issue.create_comment(f"**APR report:** Fix failed: {message}")
    issue.add_to_labels(label)

def add_label_to_issue(issue_number, label):
    repo = get_repo()
    issue = repo.get_issue(int(issue_number))
    issue.add_to_labels(label)
    logging.info(f"Added label '{label}' to issue #{issue.number}")


def report_to_pr(context):
    branch_name = context["state"]["branch"]
    target = context["config"].get("main_branch", "main")
    try:
        repo = get_repo()
        repo_owner_login = repo.owner.login

        pr_title = f"Fix for issue #{context['bug']['number']}: {context['bug']['title']}"

        pr_body = build_pr_body(context)

        existing_pr_for_branch = None
        head_branch_ref = f"{repo_owner_login}:{branch_name}"
        open_pulls = repo.get_pulls(state='open', head=head_branch_ref, base=target)
        if open_pulls.totalCount > 0:
            existing_pr_for_branch = open_pulls[0]

        if existing_pr_for_branch:
            logging.info(f"Found existing PR #{existing_pr_for_branch.number}. Updating it.")
            existing_pr_for_branch.edit(title=pr_title, body=pr_body)
            # existing_pr.create_issue_comment("This PR has been automatically updated with the latest fixes.")
            logging.info(f"Successfully updated PR #{existing_pr_for_branch.number}: {pr_title}")
        else:
            logging.info(f"Creating new PR for branch '{branch_name}' into 'main'.")
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=target
            )
            logging.info(f"Successfully created PR #{pr.number}: {pr_title}")

        # add label to issue
        fix_submitted_label = context["config"].get("submitted_fix_label")
        add_label_to_issue(context["bug"]["number"], fix_submitted_label)

    except Exception as e:
        raise RuntimeError(f"Error creating/updating PR: {str(e)}")


def build_pr_body(context):
    pr_body = f"fixes #{context['bug']['number']}\n\n"
    pr_body += "## Changes\n"
    fixed_files = context["files"].get("fixed_files", [])
    pr_body += "### Modified files:\n"

    for file_path in fixed_files:
        pr_body += f"- `{file_path}`\n"

    if context["config"].get("test_cmd"):
        test_results = context["attempts"][-1].get("test_results", {})
        if test_results:
            pr_body += "\n### Test Results\n"
            pr_body += f"Status: {test_results.get('status', 'Unknown')}\n"

    else:
        pr_body += "\n### No tests were run for this fix.\n"

    pr_body += "\n## APR Data\n"
    pr_body += f"""
                Attempts: {context['state']['current_attempt']}\n
                Tokens used: {context['metrics']['tokens']}\n
                Time taken: {context['state']['current_attempt']}\n
                """

    return pr_body
