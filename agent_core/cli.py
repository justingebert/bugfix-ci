import importlib, os, pathlib, sys, json
from agent_core.issue_helper import get_bug
from agent_core.util import _read_yaml
from dotenv import load_dotenv

#for local without docker
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

local_work_space = "../workspace" if os.getenv("ENV") == "dev-deployed" else ".."

def load_cfg() -> dict:
    cfg = {"stages": []}

    default_path = pathlib.Path("/default-config.yml")
    if default_path.exists():
        cfg |= _read_yaml(default_path)

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


def main() -> int:

    cfg = load_cfg()
    bug = get_bug()
    stages = ["localize"] #, "fix", "build", "test", "report"]

    ctx = {
        "bug": bug,
        "workspace": "/workspace",
        "logs": [],
        "cfg": cfg
    }

    for name in stages:
        print(ctx)
        stage_cls = resolve_stage(name)
        ctx = stage_cls().run(ctx)

    print("== DONE ==")
    print(json.dumps(ctx["logs"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
