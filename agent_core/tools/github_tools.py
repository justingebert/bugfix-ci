import logging

from github import Github, Issue
import os, sys

def get_repo() -> "github.Repository.Repository":
    token = os.getenv("GITHUB_TOKEN")
    repo  = os.getenv("GITHUB_REPO")
    if not token or not repo:
        sys.exit("❌  GITHUB_TOKEN and GITHUB_REPO env vars are required ❌")
    return Github(token).get_repo(repo)

def get_issues(limit, cfg) -> list[Issue.Issue]:
    repo = get_repo()
    label = cfg.get("to_fix_label")
    if not label:
        sys.exit("❌  LABEL required in CONFIG ❌")

    exclude_labels = [cfg.get("failed_fix_label", "")]
    exclude_labels.append(cfg.get("fix_submitted_label", ""))
    issues = []
    for issue in repo.get_issues(state="open", labels=[label]):
        # Skip issues that have any of the excluded labels
        should_exclude = False
        for label in issue.labels:

            if exclude_labels and label.name in exclude_labels:
                should_exclude = True
                break

        if not should_exclude:
            issues.append(issue)

        if len(issues) >= limit:
            break

    return issues

def report_failure(issue_number, message):
    repo = get_repo()
    issue = repo.get_issue(int(issue_number))
    issue.create_comment(f"❌  Fix failed: {message}")
    issue.add_to_labels("bug-fix-failed")

def add_issue_label(issue_number, label):
    repo = get_repo()
    issue = repo.get_issue(int(issue_number))
    issue.add_to_labels(label)
    logging.info(f"Added label '{label}' to issue #{issue.number}")