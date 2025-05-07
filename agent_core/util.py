import importlib
import pathlib, yaml

def _read_yaml(path: pathlib.Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh) or {}

def load_cfg(local_work_space="workspace") -> dict:
    cfg = {"stages": []}

    default_path = pathlib.Path("agent_core/default-config.yml")
    if default_path.exists():
        cfg |= _read_yaml(default_path)
        print(f"[info] loaded default config from {default_path}")
    else:
        print(f"[warn] default config file {default_path} not found; using built-ins.")

    env_path = pathlib.Path(local_work_space) / "config" / "bugfix.yml"
    if env_path.exists():
        cfg |= _read_yaml(env_path)
    else:
        print(f"[warn] config file {env_path} not found; "
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

