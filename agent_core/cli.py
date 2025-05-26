import json, logging, os, sys, time
from datetime import datetime
from pathlib import Path

from agent_core.tools.issue_helper import get_bug, get_issues, report_failure
from agent_core.util.util import load_cfg, resolve_stage, generate_feedback
from agent_core.util.logger import setup_logging, create_log_dir
from agent_core.tools.repo_tools import reset_to_main

local_work_space = "workspace" if os.getenv("ENV") == "dev-deployed" else ""

#TODO rollback after issue is attempted so next one starts at main head

def main():
    script_start_time = time.monotonic()
    log_dir = create_log_dir()

    cfg = load_cfg(local_work_space)

    localize_stages = ["localize"]
    fix_stages = ["fix"]
    validate_stages = ["build", "test"]
    apply_stages = ["apply", "report"]

    issues = get_issues(limit=2)

    pipeline_metrics = {
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "issues_processed": [],
        "successful_repairs": 0,
        "total_issues": len(issues),
        "total_execution_time": 0.0
    }

    for issue in issues:
        issue_start_time = time.monotonic()
        log_file = setup_logging(issue.number, log_dir)
        metrics_file = log_dir / f"issue_{issue.number}_metrics.json"

        logging.info(f"=== Starting bug fix for issue #{issue.number}: {issue.title} ===")

        ctx = {
            "bug": issue,
            "workspace": "/workspace",
            "cfg": cfg,
            "metrics": {
                "github_run_id": os.getenv("GITHUB_RUN_ID"),
                "issue_number": issue.number,
                "issue_title": issue.title,
                "execution_times_stages": {},
                "total_script_execution_time": 0.0,
                "repair_successful": False,
                "attempts": 1
            },
            "attempt_history": []
        }

        localize_success = True
        for name in localize_stages:
            stage_cls = resolve_stage(name)
            success, ctx = stage_cls().execute(ctx)
            if not success:
                localize_success = False
                break

        if not localize_success:
            logging.error(f"!! Localization failed for issue #{issue.number}. Skipping.")
            continue

        attempt = 0
        max_attempts = 3
        fix_success = False

        while attempt < max_attempts and not fix_success:
            attempt += 1
            ctx["metrics"]["current_attempt"] = attempt
            ctx["metrics"]["total_attempts"] = attempt

            logging.info(f"=== Attempt {attempt}/{max_attempts} for issue #{issue.number} ===")

            # Add history/context from previous attempts
            if attempt > 1:
                feedback = generate_feedback(ctx)
                ctx["previous_attempt_feedback"] = feedback
                logging.info(f"Adding feedback from previous attempt")
                logging.info(f"Feedback: {feedback[:200]}...")

            fix_stage_success = True
            for name in fix_stages:
                stage_cls = resolve_stage(name)
                success, ctx = stage_cls().execute(ctx)
                if not success:
                    fix_stage_success = False
                    break

            if not fix_stage_success:
                logging.error(f"!! Fix stage failed on attempt {attempt}")
                continue

            validation_success = True
            for name in validate_stages:
                stage_cls = resolve_stage(name)
                success, ctx = stage_cls().execute(ctx)
                if not success:
                    validation_success = False
                    break

            # Check if fix was successful
            fix_success = ctx.get("test_results", {}).get("status") == "success"

            attempt_result = {
                "attempt": attempt,
                "success": fix_success,
                "fix_stage_success": fix_stage_success,
                "validation_success": validation_success,
                "test_results_summary": ctx.get("test_results", {}).get("status", "unknown")
            }
            ctx["attempt_history"].append(attempt_result)

            if fix_success:
                ctx["metrics"]["repair_successful"] = True
                logging.info(f"=== Repair successful on attempt {attempt}/{max_attempts} ===")
                pipeline_metrics["successful_repairs"] += 1
            elif attempt < max_attempts:
                logging.info(f"=== Repair failed on attempt {attempt}/{max_attempts}, trying again ===")
            else:
                logging.info(f"=== All {max_attempts} repair attempts failed ===")

        if fix_success:
            for name in apply_stages:
                stage_cls = resolve_stage(name)
                success, ctx = stage_cls().execute(ctx)
                if not success:
                    logging.warning(f"!! Post-processing stage {name} failed")
        else:
            report_failure(issue.number, "Repair failed after max attempts")

        reset_to_main()

        issue_end_time = time.monotonic()
        issue_duration = round(issue_end_time - issue_start_time, 4)
        ctx["metrics"]["script_execution_time_for_issue"] = issue_duration

        pipeline_metrics["issues_processed"].append({
            "issue_number": issue.number,
            "issue_title": issue.title,
            "repair_successful": fix_success,
            "execution_time": issue_duration
        })

        with open(metrics_file, 'w') as f:
            json.dump({
                "issue_number": issue.number,
                "issue_title": issue.title,
                "metrics": ctx["metrics"],
                "fixed_files": ctx.get("fixed_files", []),
                "context": {k: v for k, v in ctx.items() if k != "bug"},
            }, f, indent=2)

        logging.info(f"== DONE == Metrics saved to {metrics_file}")
        logging.info(f"Log file: {log_file}")

    script_end_time = time.monotonic()
    total_duration = script_end_time - script_start_time
    pipeline_metrics["total_execution_time"] = round(total_duration, 4)
    pipeline_file = Path(log_dir) / "pipeline_results.json"
    with open(pipeline_file, 'w') as f:
        json.dump(pipeline_metrics, f, indent=2)

    logging.info(f"Pipeline complete in {total_duration:.4f} seconds")
    logging.info(f"Processed {len(issues)} issues with {pipeline_metrics['successful_repairs']} successful repairs")
    logging.info(f"Pipeline results saved to {pipeline_file}")


if __name__ == "__main__":
    sys.exit(main())
