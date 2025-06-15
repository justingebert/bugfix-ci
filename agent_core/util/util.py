import importlib, logging, pathlib, yaml, json, os
def get_local_workspace():
    return pathlib.Path("/workspace")

def _read_yaml(path: pathlib.Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def load_cfg(work_space=None) -> dict:
    cfg = {"stages": []}

    default_path = pathlib.Path("agent_core/default-config.yml")
    if default_path.exists():
        cfg |= _read_yaml(default_path)
        logging.info(f"[info] loaded default config from {default_path}")
    else:
        logging.info(f"[warn] default config file {default_path} not found; using built-ins.")

    env_path = pathlib.Path(work_space) / "config" / "bugfix.yml"
    if env_path.exists():
        cfg |= _read_yaml(env_path)
        logging.info(f"[info] loaded config from {env_path}")
    else:
        logging.info(f"[warn] config file {env_path} not found; "
                     f"using {default_path.name if default_path.exists() else 'built-ins'}.")
    return cfg


def get_issues_from_env():
    issues_json = os.environ.get("FILTERED_ISSUES")
    if not issues_json:
        return []

    issues_data = json.loads(issues_json)

    return issues_data

import difflib


def generate_feedback(context):
    """Generate feedback from test results and code changes for the next fix attempt"""

    attempts = context.get("attempts", [])

    if not context or len(context) <= 1:
        return ""


    original_files = context.get("files", {}).get("source_files", {})
    feedback = ""
    # Exclude current attempt (last one in the list)
    previous_attempts = attempts[:-1]
    
    for idx, attempt in enumerate(previous_attempts, 1):
        feedback = f"Attempt #{idx+1}:"

        edited_files = attempt["stages"]["fix"]["results"]["files_content"]

        if original_files and edited_files:
            feedback += "Code Changes:\n"
            
            # Compare each file that was edited
            for file_path, edited_content in edited_files.items():
                if file_path in original_files:
                    original_content = original_files[file_path]
                    
                    # Only generate diff if content actually changed
                    if original_content != edited_content:
                        feedback += f"\n--- Changes in {file_path} ---\n"
                        
                        diff = difflib.unified_diff(
                            original_content.splitlines(keepends=True),
                            edited_content.splitlines(keepends=True),
                            fromfile=f'original/{file_path}',
                            tofile=f'attempt_{idx}/{file_path}',
                            n=3
                        )
                        diff_text = ''.join(diff)
                        
                        if diff_text:
                            feedback += "```diff\n"
                            feedback += diff_text
                            feedback += "```\n"
                        else:
                            feedback += "Files are identical (no diff generated)\n"
                    else:
                        feedback += f"\n--- {file_path}: NO CHANGES ---\n"

        if attempt.get("stages").get("build", {}):
            feedback += "\nBuild Results:\n"
            build_results = attempt.get("stages").get("build").get("status", {})
            build_details = attempt.get("stages").get("build").get("details", {})
            feedback += f"Status: {build_results}\n"
            feedback += f"Details: {build_details}\n"

        if attempt.get("stages").get("test", {}):
            feedback += "\nTest Results:\n"
            test_results = attempt.get("stages").get("test").get("status", {})
            test_details = attempt.get("stages").get("test").get("details", {})
            feedback += f"Status: {test_results}\n"
            feedback += f"Details: {test_details}\n"


    return feedback
