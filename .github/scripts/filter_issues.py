# .github/scripts/filter_issues.py
import json
import os
import sys
import yaml
from github import Github

event_name = os.environ.get("GITHUB_EVENT_NAME", "")
event_path = os.environ.get("GITHUB_EVENT_PATH", "")
with open(event_path) as f:
    event = json.load(f)

#TODO: add default config file
config_path = "config/bugfix.yml"
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
else:
    print("Config file not found")
    sys.exit(1)

to_fix_label = config.get("to_fix_label", "bug_v01")
submitted_fix_label = config.get("submitted_fix_label", "bug_v01_submitted_fix")
failed_fix_label = config.get("failed_fix_label", "bug-fix-failed")
max_issues = config.get("max_issues", 5)

github_token = os.environ.get("GITHUB_TOKEN")
g = Github(github_token)
repo = g.get_repo(os.environ.get("GITHUB_REPOSITORY"))

issues_to_process = []

if event_name == "workflow_dispatch":
    issues = repo.get_issues(state="open", labels=[to_fix_label], sort="created", direction="desc")
    count = 0
    for issue in issues:
        # Skip issues that have been processed and ahve the submitted fix label or failed fix label
        if submitted_fix_label in [label.name for label in issue.labels]:
            continue

        if failed_fix_label in [label.name for label in issue.labels]:
            continue

        issues_to_process.append({
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "labels": [{"name": label.name} for label in issue.labels],
        })
        count += 1
        if count >= max_issues:
            break

elif event_name == "issues":
    action = event.get("action", "")
    issue_data = event.get("issue", {})
    issue_number = issue_data.get("number")
    issue_labels = [label.get("name") for label in issue_data.get("labels", [])]

    if submitted_fix_label in issue_labels:
        sys.exit(0)

    # Process if issue has to_fix_label
    if to_fix_label in issue_labels:
        issue = repo.get_issue(issue_number)
        issues_to_process.append({
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "labels": [{"name": label.name} for label in issue.labels],
            "url": issue.html_url
        })
    # elif failed_fix_label in issue_labels and action == "edited":
    #     issue = repo.get_issue(issue_number)
    #     issues_to_process.append({
    #         "number": issue.number,
    #         "title": issue.title,
    #         "body": issue.body,
    #         "labels": [{"name": label.name} for label in issue.labels],
    #         "url": issue.html_url
    #     })


elif event_name == "issue_comment" and event.get("action") == "created":
    issue_data = event.get("issue", {})
    issue_number = issue_data.get("number")
    issue = repo.get_issue(issue_number)

    label_names = [label.name for label in issue.labels]

    # If it has failed_fix_label but not submitted_fix_label, process it
    if failed_fix_label in label_names and submitted_fix_label not in label_names:
        issues_to_process.append({
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "labels": [{"name": label.name} for label in issue.labels],
            "url": issue.html_url
        })

issues_json = json.dumps(issues_to_process)
print(issues_json)
with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
    f.write(f"issues<<EOF\n{issues_json}\nEOF\n")