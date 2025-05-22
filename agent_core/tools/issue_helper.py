from github import Github, Issue
import os, sys

def get_repo() -> "github.Repository.Repository":
    token = os.getenv("GITHUB_TOKEN")
    repo  = os.getenv("GITHUB_REPO")
    if not token or not repo:
        sys.exit("❌  GITHUB_TOKEN and GITHUB_REPO env vars are required ❌")
    return Github(token).get_repo(repo)

def get_bug() -> Issue.Issue:
    repo = get_repo()
    manual = os.getenv("ISSUE_NUMBER")
    label = os.getenv("LABEL")
    if manual:
        return repo.get_issue(int(manual))

    for issue in repo.get_issues(state="open", labels=[label]):
        return issue
    sys.exit(f"❌  No open issues with label '{label}'")

def get_issues(limit=None) -> list[Issue.Issue]:
    repo = get_repo()
    label = os.getenv("LABEL")
    if not label:
        sys.exit("❌  LABEL env var is required ❌")

    exclude_label = os.getenv("FAILURE_LABEL")

    issues = []
    for issue in repo.get_issues(state="open", labels=[label]):
        # Skip issues that have any of the excluded labels
        should_exclude = False
        for label in issue.labels:
            if exclude_label and label.name == exclude_label:
                should_exclude = True
                break

        if not should_exclude:
            issues.append(issue)

        if limit and len(issues) >= limit:
            break

    return issues

def report_failure(issue_number, message):
    repo = get_repo()
    issue = repo.get_issue(int(issue_number))
    issue.create_comment(f"❌  Fix failed: {message}")
    issue.add_to_labels("bug-fix-failed")