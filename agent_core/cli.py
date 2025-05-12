import os, sys
import time
from pprint import pprint

from agent_core.tools.issue_helper import get_bug
from agent_core.util import load_cfg, resolve_stage

local_work_space = "workspace" if os.getenv("ENV") == "dev-deployed" else ""

def main():
    script_start_time = time.monotonic()
    cfg = load_cfg(local_work_space)
    bug = get_bug()
    stages = ["localize", "fix", "build", "test", "apply", "report"]

    ctx = {
        "bug": bug,
        "workspace": "/workspace",
        "logs": [],
        "cfg": cfg,
        "metrics": {
            "github_run_id": os.getenv("GITHUB_RUN_ID"),
            "execution_times_stages": {},
            "total_script_execution_time": 0.0,
            "execution_time_in_ci_cd": 0.0,
            "repair_successful": False,
            "attempts": 1
        }
    }

    for name in stages:
        stage_start_time = time.monotonic()
        try:
            stage_cls = resolve_stage(name)
            ctx = stage_cls().run(ctx)
            stage_end_time = time.monotonic()
            stage_duration = stage_end_time - stage_start_time
            ctx["metrics"]["execution_times_stages"][name] = round(stage_duration, 4)
            print(f"== Stage {name} completed in {stage_duration:.4f} seconds ==")
        except Exception as e:
            stage_end_time = time.monotonic()
            stage_duration = stage_end_time - stage_start_time
            ctx["metrics"]["execution_times_stages"][name] = round(stage_duration, 4)
            print(f"!! Stage {name} failed after {stage_duration:.4f} seconds: {e}")


    script_end_time = time.monotonic()
    ctx["metrics"]["total_script_execution_time"] = round(script_end_time - script_start_time, 4)

    print("== DONE ==")
    pprint(ctx, indent=2)


if __name__ == "__main__":
    sys.exit(main())
