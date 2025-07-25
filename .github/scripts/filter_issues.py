import json, os, sys, yaml
from github import Github

event_name = os.environ.get("GITHUB_EVENT_NAME", "")
event_path = os.environ.get("GITHUB_EVENT_PATH", "")
with open(event_path) as f:
    event = json.load(f)

config = {
    "to_fix_label": "bug_v01",
    "submitted_fix_label": "bug_v01_fix_submitted",
    "failed_fix_label": "bug_v01_fix_failed",
    "workdir": "",
    "branch_prefix": "bugfix_v01_",
    "main_branch": "main",
    "max_issues": 10,
    "max_attempts": 3,
    "provider": "google",
    "model": "gemini-2.0-flash",
}

custom_config_path = "bugfix.yml"
if os.path.exists(custom_config_path):
    with open(custom_config_path, "r") as f:
        config = yaml.safe_load(f)
else:
    print("no custom config file found falling back to default")

github = Github(os.environ.get("GITHUB_TOKEN"))
repo = github.get_repo(os.environ.get("GITHUB_REPOSITORY"))

issues_to_process = []

if event_name == "workflow_dispatch" or event_name == "cron":
    issues = repo.get_issues(state="open", labels=[config["to_fix_label"]], sort="created", direction="desc")
    count = 0
    for issue in issues:
        issue_labels = [label.name for label in issue.labels]
        # Skip issues that have been processed already
        if config["submitted_fix_label"] in issue_labels or config["failed_fix_label"] in issue_labels:
            continue

        issues_to_process.append({
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "labels": issue_labels,
        })

        count += 1

        if count >= config["max_issues"]:
            break

elif event_name == "issues":
    action = event.get("action", "")
    issue = event.get("issue", {})
    issue_labels = [label.get("name") for label in issue.get("labels", [])]

    if config["submitted_fix_label"] in issue_labels or config["failed_fix_label"] in issue_labels:
        sys.exit(0)

    if config["to_fix_label"] in issue_labels:
        issues_to_process.append({
            "number": issue["number"],
            "title": issue["title"],
            "body": issue["body"],
            "labels": issue_labels,
        })

elif event_name == "issue_comment" and event.get("action") == "created":
    comment_body = event.get("comment", {}).get("body", "")

    if comment_body.startswith("**APR report:**"):
        print("Failure comment from APR, skipping.")
        sys.exit(0)

    issue = event.get("issue", {})

    issue_labels = [label.get("name") for label in issue.get("labels", [])]

    if config["failed_fix_label"] in issue_labels and config["submitted_fix_label"] not in issue_labels:
        issues_to_process.append({
            "number": issue["number"],
            "title": issue["title"],
            "body": issue["body"],
            "labels": issue_labels,
        })

if not issues_to_process:
    print("No issues to process")
    sys.exit(0)

print(f"Found {len(issues_to_process)} issues to process")
issues_json = json.dumps(issues_to_process)
print(issues_json)
with open(os.environ.get("GITHUB_OUTPUT"), "a") as f:
    f.write(f"issues<<EOF\n{issues_json}\nEOF\n")