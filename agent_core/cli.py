import importlib, os, pathlib, sys, yaml, json
from agent_core.util import print_dir_tree


def _read_yaml(path: pathlib.Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def load_cfg() -> dict:
    """Return merged configuration."""
    cfg = {"stages": []}

    default_path = pathlib.Path("/workspace/config/defaultconfig.yml")
    if default_path.exists():
        cfg |= _read_yaml(default_path)

    env_path = pathlib.Path(os.getenv("CONFIG_FILE", "/workspace/config/bugfix.yml"))
    if env_path.exists():
        cfg |= _read_yaml(env_path)
    else:
        print(f"[warn] config file {env_path} not found; "
              f"using {default_path.name if default_path.exists() else 'built-ins'}.")

    # guarantee a stages list so orchestrator never crashes
    cfg.setdefault("stages", [])

    return cfg


def resolve_stage(name: str):
    """Import `agent_core.stages.<name>` and return its 'Stage' class."""
    module_path = f"agent_core.stages.{name}"
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise RuntimeError(f"Stage '{name}': module '{module_path}' not found") from e
    try:
        stage_cls = getattr(module, "Stage")
    except AttributeError as e:
        raise RuntimeError(f"Stage '{name}': 'Stage' class missing in {module_path}") from e
    return stage_cls


def main() -> int:

    print_dir_tree()

    cfg = load_cfg()
    stages = cfg["stages"]

    ctx = {"workspace": "/workspace", "logs": [], "cfg": cfg}

    for name in stages:
        stage_cls = resolve_stage(name)
        ctx = stage_cls().run(ctx)

    print("== DONE ==")
    print(json.dumps(ctx["logs"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
