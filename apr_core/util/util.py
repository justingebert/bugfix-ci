import importlib, logging, pathlib, yaml, json, os
def get_local_workspace():
    return pathlib.Path("/workspace")

def _read_yaml(path: pathlib.Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_config(work_space=None) -> dict:
    config = {}

    default_path = pathlib.Path("apr_core/default-config.yml")
    if default_path.exists():
        config |= _read_yaml(default_path)
        logging.info(f"[info] loaded default config from {default_path}")
    else:
        logging.info(f"[warn] default config file {default_path} not found; using built-ins.")

    custom_path = pathlib.Path(work_space) / "bugfix.yml"
    if custom_path.exists():
        config |= _read_yaml(custom_path)
        logging.info(f"[info] loaded config from {custom_path}")
    else:
        logging.info(f"[warn] config file {custom_path} not found; "
                     f"using {default_path.name if default_path.exists() else 'built-ins'}.")
    return config


def get_issues_from_env():
    issues_json = os.environ.get("FILTERED_ISSUES")
    if not issues_json:
        return []

    return json.loads(issues_json)