import importlib, logging, pathlib, yaml
from datetime import datetime

def _read_yaml(path: pathlib.Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh) or {}

def load_cfg(local_work_space="workspace") -> dict:
    cfg = {"stages": []}

    default_path = pathlib.Path("agent_core/default-config.yml")
    if default_path.exists():
        cfg |= _read_yaml(default_path)
        logging.info(f"[info] loaded default config from {default_path}")
    else:
        logging.info(f"[warn] default config file {default_path} not found; using built-ins.")

    env_path = pathlib.Path(local_work_space) / "workspace" / "config" / "bugfix.yml"
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


def setup_logging(issue_number):
    """Configure logging to write to both console and file"""
    # Create logs directory
    log_dir = pathlib.Path("/workspace/logs")
    logging.info(f"Creating log directory at: {log_dir.absolute()}")
    log_dir.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"issue_{issue_number}_{timestamp}.log"

    # Reset handlers (in case this function is called multiple times)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure file and console handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return log_dir, log_file

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