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