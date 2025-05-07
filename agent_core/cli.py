import importlib, os, pathlib, sys, json
from agent_core.issue_helper import get_bug
from dotenv import load_dotenv
from agent_core.util import load_cfg, resolve_stage

local_work_space = "../workspace" if os.getenv("ENV") == "dev-deployed" else "workspace"

def main():

    cfg = load_cfg(local_work_space)
    bug = get_bug()
    stages = ["localize", "fix", "build", "test"] #, "report"]

    ctx = {
        "bug": bug,
        "workspace": "/workspace",
        "logs": [],
        "cfg": cfg
    }

    for name in stages:
        stage_cls = resolve_stage(name)
        ctx = stage_cls().run(ctx)

    print("== DONE ==")
    print(ctx)


if __name__ == "__main__":
    sys.exit(main())
