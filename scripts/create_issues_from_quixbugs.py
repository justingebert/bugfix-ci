from pathlib import Path
from github import Github
import os, textwrap, sys
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

BUG_DIR = REPO_ROOT / "datasets" / "quixbugs" / "python_programs"
ISSUE_LABELS = ["bug_v01"]

def main() -> None:
    token     = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")

    if not token or not repo_name:
        sys.exit("❌ GITHUB_TOKEN or GITHUB_REPOSITORY missing in env ❌")

    gh   = Github(token)
    repo = gh.get_repo(repo_name)

    existing_titles = {i.title for i in repo.get_issues(state="all")}
    exclude_ids = {
        "node",
        "breadth_first_search_test",
        "depth_first_search_test",
        "detect_cycle_test",
        "reverse_linked_list_test",
        "shortest_path_length_test",
        "shortest_path_lengths_test",
        "shortest_paths_test",
        "topological_ordering_test",
    }

    for py_file in sorted(BUG_DIR.glob("*.py")):
        bug_id = py_file.stem

        if bug_id in exclude_ids:
            continue

        title   = f"Problem in {bug_id}"

        if title in existing_titles:
            print(f"• skip '{title}' (already exists)")
            continue

        body = textwrap.dedent(
            f"""
            There is a bug in **`{bug_id}`**.
            """

        ).strip()

        issue = repo.create_issue(title=title, body=body, labels=ISSUE_LABELS)
        print(f"✔ created issue #{issue.number}: {title}")


if __name__ == "__main__":
    main()