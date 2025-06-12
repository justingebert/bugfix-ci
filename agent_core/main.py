import json, logging, os, sys, time
from pathlib import Path

from agent_core.stages.apply import Apply
from agent_core.stages.build import Build
from agent_core.stages.fix import Fix
from agent_core.stages.localize import Localize
from agent_core.stages.push import Push
from agent_core.stages.report import Report
from agent_core.stages.test import Test
from agent_core.tools.github_tools import  report_failure
from agent_core.util.util import load_cfg, generate_feedback, get_local_workspace, get_issues_from_env
from agent_core.util.logger import setup_logging, create_log_dir
from agent_core.tools.local_repo_tools import checkout_branch, reset_to_main

#TODO rollback after issue is attempted so next one starts at main head
#TODO check out issue branch before starting
def main():
    script_start_time = time.monotonic()
    log_dir = create_log_dir()
    setup_logging("bugfix_pipeline", log_dir)

    cfg = load_cfg(get_local_workspace())

    pipeline_metrics = {
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "issues_processed": [],
        "successful_repairs": 0,
        "total_execution_time": 0.0
    }

    issues = get_issues_from_env()
    pipeline_metrics["issues_count"] = len(issues)

    for issue in issues:
        try:
            issue_start_time = time.monotonic()
            log_file = setup_logging(issue["number"], log_dir)
            metrics_file = log_dir / f"issue_{issue['number']}_metrics.json"

            logging.info(f"=== Starting bug fix for issue #{issue['number']}: {issue['title']} ===")

            context = {
                "bug": issue,
                "cfg": cfg,

                "state": {
                    "current_stage": None,
                    "current_attempt": 0,
                    "branch": None,
                    "repair_successful": False
                },

                "files": {
                    "source_files": [],
                    "fixed_files": [],
                    "diff_file": None,
                    "log_dir": str(log_dir),
                },

                "stages": {

                },

                "attempts": [],

                "metrics": {
                    "github_run_id": os.getenv("GITHUB_RUN_ID"),
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "execution_times_stages": {},
                    "total_script_execution_time": 0.0,
                    "repair_successful": False,
                    "attempts": 1
                },
            }

            context["state"]["branch"] = checkout_branch(issue["number"], context.get("cfg").get("branch_prefix"))

            context = Localize().execute(context)
        
            current_attempt = 0
            max_attempts = context["cfg"].get("max_attempts", 3)
            repair_successful = False

            while not repair_successful and current_attempt < max_attempts:
                current_attempt += 1
                context["state"]["current_attempt"] = current_attempt

                logging.info(f"=== Attempt {current_attempt}/{max_attempts} for issue #{issue['number']} ===")

                attempt_data = {
                    "attempt": current_attempt,
                    "stages": {},
                    "success": False
                }
                context["attempts"].append(attempt_data)

                #TODO
                #if current_attempt > 1:
                    #feedback = generate_feedback(context)
                    #context["previous_attempt_feedback"] = feedback
                    #logging.info(f"Added feedback from previous attempt")

                context = Fix().execute(context, retry=True)
                
                context = Build().execute(context, retry=True)
                
                if context["cfg"].get("test_cmd"):
                    context = Test().execute(context, retry=True)
                
                repair_successful = context["state"].get("repair_successful", False)
                
                if repair_successful:
                    context["attempts"][-1]["success"] = True
                    logging.info(f"=== Repair successful on attempt {current_attempt}/{max_attempts} ===")
                else:
                    if current_attempt < max_attempts:
                        logging.info(f"=== Repair failed on attempt {current_attempt}/{max_attempts}, trying again ===")
                    else:
                        logging.info(f"=== All {max_attempts} repair attempts failed ===")


            if repair_successful:
                context = Apply().execute(context)
                context = Push().execute(context)
                #context = Report().execute(context)
                pipeline_metrics["successful_repairs"] += 1
            else:
                report_failure(issue["number"], "Repair failed after max attempts")

            # for local usage (not in GitHub Actions)
            reset_to_main()
            
            issue_duration = round(time.monotonic() - issue_start_time, 4)
            context["metrics"]["script_execution_time_for_issue"] = issue_duration
            pipeline_metrics["issues_processed"].append({
                "issue_number": issue["number"],
                "issue_title": issue["title"],
                "repair_successful": repair_successful,
                "execution_time": issue_duration
            })

            with open(metrics_file, 'w') as f:
                json.dump(context, f, indent=2)

            logging.info(f"== DONE == Metrics saved to {metrics_file}")
            logging.info(f"Log file: {log_file}")
        
        except Exception as e:
            logging.error(f"!! Error processing issue #{issue['number']}: {e}", exc_info=True)


    total_duration = time.monotonic() - script_start_time
    pipeline_metrics["total_execution_time"] = round(total_duration, 4)
    pipeline_file = Path(log_dir) / "pipeline_results.json"
    with open(pipeline_file, 'w') as f:
        json.dump(pipeline_metrics, f, indent=2)

    logging.info(f"Pipeline complete in {total_duration:.4f} seconds")
    logging.info(f"Processed {len(issues)} issues with {pipeline_metrics['successful_repairs']} successful repairs")

if __name__ == "__main__":
    sys.exit(main())
