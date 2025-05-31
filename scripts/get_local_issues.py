import json
import os
import sys
import yaml
from github import Github
from dotenv import load_dotenv


def get_filtered_issues():
    load_dotenv()

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
    if not github_token:
        print("GITHUB_TOKEN not found in environment")
        sys.exit(1)

    repo_name = os.environ.get("GITHUB_REPO")
    if not repo_name:
        print("GITHUB_REPO not found in environment")
        sys.exit(1)

    g = Github(github_token)
    repo = g.get_repo(repo_name)

    issues_to_process = []
    issues = repo.get_issues(state="open", labels=[to_fix_label], sort="created", direction="desc")
    count = 0

    for issue in issues:
        issue_labels = [label.name for label in issue.labels]
        if submitted_fix_label in issue_labels or failed_fix_label in issue_labels:
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

    return issues_to_process


if __name__ == "__main__":
    output_file = sys.argv[1] if len(sys.argv) > 1 else "../filtered_issues.json"

    env_file = "../.docker-env-issues"

    filtered_issues = get_filtered_issues()

    with open(output_file, "w") as f:
        json.dump(filtered_issues, f, indent=2)

    with open(env_file, "w") as f:
        f.write(f"FILTERED_ISSUES={json.dumps(filtered_issues)}")

    print(f"Filtered {len(filtered_issues)} issues to {output_file}")