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

    if limit:
        return [issue for issue in repo.get_issues(state="open", labels=[label])][:limit]
    else:
        return [issue for issue in repo.get_issues(state="open", labels=[label])]