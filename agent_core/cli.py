import json, logging, os, sys, time
from datetime import datetime
from pathlib import Path

from agent_core.tools.issue_helper import get_bug, get_issues
from agent_core.util import load_cfg, resolve_stage, setup_logging

local_work_space = "workspace" if os.getenv("ENV") == "dev-deployed" else ""

def main():
    script_start_time = time.monotonic()

    cfg = load_cfg(local_work_space)
    issues = get_issues(limit=1)
    stages = ["localize", "fix", "build", "test"]

    pipeline_metrics = {
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "issues_processed": [],
        "successful_repairs": 0,
        "total_issues": len(issues),
        "total_execution_time": 0.0
    }

    for issue in issues:
        issue_start_time = time.monotonic()
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


        successful = ctx.get("test_results", {}).get("status") == "success"
        if successful:
            pipeline_metrics["successful_repairs"] += 1


        issue_end_time = time.monotonic()
        issue_duration = round(issue_end_time - issue_start_time, 4)
        ctx["metrics"]["script_execution_time_for_issue"] = issue_duration

        pipeline_metrics["issues_processed"].append({
            "issue_number": issue.number,
            "issue_title": issue.title,
            "repair_successful": successful,
            "execution_time": issue_duration
        })

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

    script_end_time = time.monotonic()
    total_duration = script_end_time - script_start_time
    pipeline_metrics["total_execution_time"] = round(total_duration, 4)
    pipeline_file = Path(log_dir) / f"pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(pipeline_file, 'w') as f:
        json.dump(pipeline_metrics, f, indent=2)

    logging.info(f"Pipeline complete in {total_duration:.4f} seconds")
    logging.info(f"Processed {len(issues)} issues with {pipeline_metrics['successful_repairs']} successful repairs")
    logging.info(f"Pipeline results saved to {pipeline_file}")



if __name__ == "__main__":
    sys.exit(main())
