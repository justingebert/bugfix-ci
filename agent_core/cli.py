import json, logging, os, sys, time
from pathlib import Path

from agent_core.tools.github_tools import get_issues, report_failure
from agent_core.util.util import load_cfg, resolve_stage, generate_feedback, get_local_workspace, get_issues_from_env
from agent_core.util.logger import setup_logging, create_log_dir
from agent_core.tools.local_repo_tools import reset_to_main

#TODO rollback after issue is attempted so next one starts at main head
#TODO check out issue branch before starting
def main():
    script_start_time = time.monotonic()
    log_dir = create_log_dir()
    log_file = setup_logging("bugfix_pipeline", log_dir)

    cfg = load_cfg(get_local_workspace())

    issuestest = get_issues_from_env()
    print(issuestest)
    sys.exit(0)

    localize_stages = ["localize"]
    fix_stages = ["fix"]
    validate_stages = ["build", "test"]
    #TODO report to issue aswell
    apply_stages = ["apply", "report"]

    # issues = get_issues(limit=2, cfg=cfg)

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
            "cfg": cfg,
            "attempt_history": [],
            "metrics": {
                "github_run_id": os.getenv("GITHUB_RUN_ID"),
                "issue_number": issue.number,
                "issue_title": issue.title,
                "execution_times_stages": {},
                "total_script_execution_time": 0.0,
                "repair_successful": False,
                "attempts": 1
            },
        }

        localize_success = False
        for name in localize_stages:
            stage_cls = resolve_stage(name)
            localize_success, ctx = stage_cls().execute(ctx)
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
                logging.info(f"Added feedback from previous attempt")

            fix_stage_success = False
            for name in fix_stages:
                stage_cls = resolve_stage(name)
                fix_stage_success, ctx = stage_cls().execute(ctx)

            if not fix_stage_success:
                logging.error(f"!! Fix stage failed on attempt {attempt}")
                continue

            validation_success = False
            for name in validate_stages:
                stage_cls = resolve_stage(name)
                validation_success, ctx = stage_cls().execute(ctx)

            tests_passed = ctx.get("test_results", {}).get("status") == "success"
            fix_success = tests_passed and localize_success and fix_stage_success and validation_success

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
