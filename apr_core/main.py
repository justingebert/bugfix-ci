import json
import logging
import os
import sys
import time
from pathlib import Path

from apr_core.llm.llm import LLM
from apr_core.llm.prompts import generate_feedback
from apr_core.stages import Build, Fix, Localize, Test
from apr_core.tools.github_tools import report_to_pr, report_failure
from apr_core.tools.local_repo_tools import checkout_branch, reset_files, apply_changes_to_branch, push_changes
from apr_core.util.logger import setup_logging, create_log_dir
from apr_core.util.util import load_config, get_issues_from_env, get_local_workspace


def main():
    script_start_time = time.monotonic()
    log_dir = create_log_dir()
    setup_logging("bugfix_pipeline", log_dir)

    bugfix_metrics = {
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "issues_processed": [],
        "successful_repairs": 0,
        "total_execution_time": 0.0,
    }

    config = load_config(get_local_workspace())
    llm = LLM(
        provider=config.get("provider", "google"),
        model=config.get("model", "gemini-2.0-flash"),
    )

    issues = get_issues_from_env()

    for issue in issues:
        issue_start_time = time.monotonic()
        log_file = setup_logging(f"issue{issue['number']}", log_dir)
        llm.track_nested_usage(issue["number"])

        logging.info(f"=== Starting bug fix for issue #{issue['number']}: {issue['title']} ===")

        context = {
            "bug": issue,
            "config": config,
            "state": {
                "current_stage": None,
                "current_attempt": 0,
                "branch": None,
                "repair_successful": False,
            },
            "files": {
                "source_files": [],
                "fixed_files": [],
                "diff_file": None,
                "log_dir": str(log_dir),
            },
            "stages": {},
            "attempts": [],
            "metrics": {
                "github_run_id": os.getenv("GITHUB_RUN_ID"),
                "script_execution_time": 0.0,
                "execution_repair_stages" : {},
                "tokens": {}
            },
        }

        try:
            context["state"]["branch"] = checkout_branch(
                issue["number"], prefix=context.get("config").get("branch_prefix")
            )

            context = Localize(llm=llm).execute(context)

            max_attempts = context["config"].get("max_attempts", 3)

            while not context["state"]["repair_successful"] and context["state"]["current_attempt"] < max_attempts:
                context["state"]["current_attempt"] += 1

                logging.info(f"=== Attempt {context['state']['current_attempt']}/{max_attempts} for issue #{issue['number']} ===")

                attempt_data = {
                    "attempt": context["state"]["current_attempt"],
                    "stages": {},
                    "success": False,
                }
                context["attempts"].append(attempt_data)

                if context["state"]["current_attempt"] > 1:
                    feedback = generate_feedback(context)
                    context["previous_attempt_feedback"] = feedback

                context = Fix(llm=llm).execute(context, retry=True)

                context = Build().execute(context, retry=True)

                if context["config"].get("test_cmd"):
                    context = Test().execute(context, retry=True)

                if context["state"]["repair_successful"]:
                    context["attempts"][-1]["success"] = True
                    logging.info(f"=== Repair successful on attempt {context['state']['current_attempt']}/{max_attempts} ===")
                elif context['state']['current_attempt'] < max_attempts:
                        logging.info(f"=== Repair failed on attempt {context['state']['current_attempt']}/{max_attempts}, trying again ===")
                        reset_files(context["files"]["fixed_files"])

            if context['state']['current_attempt']:
                context["files"]["diff_file"] = apply_changes_to_branch(context["state"]["branch"], context["files"]["fixed_files"], commit_info=f"#{issue['number']}: {issue['title']}")
                push_changes(context["state"]["branch"])
                report_to_pr(context)
                bugfix_metrics["successful_repairs"] += 1
            else:
                logging.info( f"=== Repair failed after {max_attempts} attempts for issue #{issue['number']} ===")
                report_failure(issue["number"], "Repair failed after max attempts", config.get("failed_fix_label"))

            reset_files(branch=context["config"]["main_branch"])

        except Exception as e:
            logging.error(f"!! Error processing issue #{issue['number']}: {e}", exc_info=True)

        finally:
            issue_duration = round(time.monotonic() - issue_start_time, 4)
            context["metrics"]["script_execution_time"] = issue_duration
            context["metrics"]["tokens"] = llm.pop_nested_usage(issue["number"])

            metrics_file = log_dir / f"issue_{issue['number']}_metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(context, f, indent=2)
                logging.info(f"== DONE == Metrics saved to {metrics_file}")

            bugfix_metrics["issues_processed"].append(
                {
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "repair_successful": context["state"]["repair_successful"],
                    "attempts": context["state"]["current_attempt"],
                    "tokens": context["metrics"]["tokens"],
                    "execution_time": issue_duration,
                }
            )

            logging.info(f"Log file: {log_file}")

            # sleep for Xsec (to avoid hitting API rate limits for free tier)
            time.sleep(4)

    bugfix_metrics["issues_count"] = len(issues)
    total_duration = time.monotonic() - script_start_time
    bugfix_metrics["total_execution_time"] = round(total_duration, 4)
    bugfix_metrics["model"] = llm.model
    bugfix_metrics["llm_usage"] = llm.get_usage()

    results_file = Path(log_dir) / "bugfix_results.json"
    with open(results_file, "w") as f:
        json.dump(bugfix_metrics, f, indent=2)

    logging.info(f"Pipeline complete in {total_duration:.4f} seconds")
    logging.info(f"Processed {len(issues)} issues with {bugfix_metrics['successful_repairs']} successful repairs")

if __name__ == "__main__":
    sys.exit(main())
