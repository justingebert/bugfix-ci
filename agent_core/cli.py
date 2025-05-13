import json, logging, os, sys, time
from agent_core.tools.issue_helper import get_bug, get_issues
from agent_core.util import load_cfg, resolve_stage, setup_logging

local_work_space = "workspace" if os.getenv("ENV") == "dev-deployed" else ""


def main():
    script_start_time = time.monotonic()
    cfg = load_cfg(local_work_space)
    issues = get_issues()
    stages = ["localize", "fix", "build", "test"]

    for issue in issues:
        log_dir, log_file = setup_logging(issue.number)
        metrics_file = log_file.with_suffix('.json')

        logging.info(f"=== Starting bug fix for issue #{issue.number}: {issue.title} ===")

        ctx = {
            "bug": issue,
            "workspace": "/workspace",
            "logs": [],
            "cfg": cfg,
            "metrics": {
                "github_run_id": os.getenv("GITHUB_RUN_ID"),
                "issue_number": issue.number,
                "issue_title": issue.title,
                "execution_times_stages": {},
                "total_script_execution_time": 0.0,
                "repair_successful": False,
                "attempts": 1
            }
        }

        for name in stages:
            stage_start_time = time.monotonic()
            try:
                stage_cls = resolve_stage(name)
                logging.info(f"== Running stage: {name} ==")
                ctx = stage_cls().run(ctx)
                stage_end_time = time.monotonic()
                stage_duration = stage_end_time - stage_start_time
                ctx["metrics"]["execution_times_stages"][name] = round(stage_duration, 4)
                logging.info(f"== Stage {name} completed in {stage_duration:.4f} seconds ==")
            except Exception as e:
                stage_end_time = time.monotonic()
                stage_duration = stage_end_time - stage_start_time
                ctx["metrics"]["execution_times_stages"][name] = round(stage_duration, 4)
                logging.error(f"!! Stage {name} failed after {stage_duration:.4f} seconds: {e}", exc_info=True)
                ctx["logs"].append(f"Error in {name} stage: {str(e)}")

        script_end_time = time.monotonic()
        ctx["metrics"]["total_script_execution_time"] = round(script_end_time - script_start_time, 4)

        with open(metrics_file, 'w') as f:
            json.dump({
                "issue_number": issue.number,
                "issue_title": issue.title,
                "metrics": ctx["metrics"],
                "logs": ctx["logs"],
                "fixed_files": ctx.get("fixed_files", [])
            }, f, indent=2)

        logging.info(f"== DONE == Metrics saved to {metrics_file}")
        logging.info(f"Log file: {log_file}")


if __name__ == "__main__":
    sys.exit(main())
