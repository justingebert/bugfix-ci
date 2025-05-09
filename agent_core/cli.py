import os, sys
from pprint import pprint

from agent_core.issue_helper import get_bug
from agent_core.util import load_cfg, resolve_stage

local_work_space = "workspace" if os.getenv("ENV") == "dev-deployed" else ""

def main():

    cfg = load_cfg(local_work_space)
    bug = get_bug()
    stages = ["localize", "fix", "build", "test", "apply", "report"]

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
    pprint(ctx, indent=2)


if __name__ == "__main__":
    sys.exit(main())
