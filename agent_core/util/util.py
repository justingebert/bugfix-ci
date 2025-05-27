import importlib, logging, pathlib, yaml

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
    else:
        logging.info(f"[warn] config file {env_path} not found; "
                     f"using {default_path.name if default_path.exists() else 'built-ins'}.")
    return cfg


def resolve_stage(name: str):
    """Import `agent_core.stages.<name>` and return its stage implementation class."""
    module_path = f"agent_core.stages.{name}"
    class_name = name.capitalize()
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise RuntimeError(f"Stage '{name}': module '{module_path}' not found") from e
    try:
        stage_cls = getattr(module, class_name)
    except AttributeError as e:
        raise RuntimeError(f"Stage '{name}': Class '{class_name}' missing in {module_path}") from e
    return stage_cls


import difflib


def generate_feedback(ctx):
    """Generate feedback from test results and code changes for the next fix attempt"""
    test_results = ctx.get("test_results", {})
    test_details = test_results.get("details", [])
    attempt = ctx["metrics"]["current_attempt"]

    feedback = f"Previous fix attempt #{attempt} failed. "

    # Add test failure information
    if test_details:
        failures = [d for d in test_details if d.get("status") == "failure"]
        if failures:
            feedback += "Test failures:\n"
            for failure in failures:
                feedback += f"- File: {failure.get('file')}\n"
                if failure.get('stdout'):
                    feedback += f"  Stdout: {failure.get('stdout')}\n"
                if failure.get('stderr'):
                    feedback += f"  Stderr: {failure.get('stderr')}\n"

    # Add diff from the original code to the current version
    original_code = ctx.get("original_code")
    current_code = ""
    if ctx.get("fixed_files"):
        file_path = ctx.get("fixed_files")[0]
        with open(file_path, 'r') as f:
            current_code = f.read()

    if original_code and current_code:
        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            current_code.splitlines(keepends=True),
            fromfile='original',
            tofile='current',
            n=3
        )
        diff_text = ''.join(diff)

        if diff_text:
            feedback += "\nChanges made in the previous attempt:\n"
            feedback += "```diff\n"
            feedback += diff_text
            feedback += "```\n"

    return feedback
