import pathlib, datetime
from agent_core.stage import Stage
from agent_core.tools.repo_tools import run_command
import logging


class Build(Stage):
    name = "build"

    def run(self, ctx):
        logging.info(f"[{self.name}] starting build process 👷")
        fixed_files = ctx.get("fixed_files", [])
        if not fixed_files:
            logging.info(f"[{self.name}] No fixed files found to build.")
            ctx["build_results"] = {"status": "skipped", "message": "No fixed files"}
            return ctx

        build_results = {"status": "success", "details": []}

        for file_path_str in fixed_files:
            file_path = pathlib.Path(file_path_str)
            if not file_path.exists():
                logging.info(f"[{self.name}] File not found: {file_path}")
                build_results["details"].append({
                    "file": str(file_path),
                    "formatter_status": "error",
                    "formatter_output": "File not found",
                    "linter_status": "error",
                    "linter_output": "File not found"
                })
                build_results["status"] = "failure"
                continue

            file_detail = {"file": str(file_path)}

            # 1. Formatting with black
            logging.info(f"[{self.name}] Formatting {file_path} with black...")
            format_success, format_stdout, format_stderr = run_command(["python", "-m", "black"], file_path)
            if not format_success:
                if "Command not found" in format_stderr or "Error running command" in format_stderr:
                    logging.info(f"[{self.name}] Error running black on {file_path}: {format_stderr}")
                    file_detail["formatter_status"] = "error"
                    file_detail["formatter_output"] = format_stderr
                    build_results["status"] = "failure"
                else:
                    logging.info(
                        f"[{self.name}] black ran on {file_path}. Output (stdout): {format_stdout}. Output (stderr): {format_stderr}")
                    file_detail["formatter_status"] = "success"
                    file_detail["formatter_output"] = f"stdout: {format_stdout}\nstderr: {format_stderr}"

            else:
                logging.info(f"[{self.name}] {file_path} formatted successfully by black.")
                file_detail["formatter_status"] = "success"
                file_detail["formatter_output"] = format_stdout + format_stderr

            # 2. Linting with flake8
            logging.info(f"[{self.name}] Linting {file_path} with flake8...")
            lint_success, lint_stdout, lint_stderr = run_command(["python", "-m", "flake8"], file_path)

            if "Command not found" in lint_stderr or "Error running command" in lint_stderr:
                logging.info(f"[{self.name}] Error running flake8 on {file_path}: {lint_stderr}")
                file_detail["linter_status"] = "error"
                file_detail["linter_output"] = lint_stderr
                build_results["status"] = "failure"
            elif not lint_success:
                logging.info(f"[{self.name}] flake8 found issues in {file_path}:\n{lint_stdout}{lint_stderr}")
                file_detail["linter_status"] = "issues_found"
                file_detail["linter_output"] = lint_stdout + lint_stderr
                build_results["status"] = "failure"
            else:
                logging.info(f"[{self.name}] {file_path} linted successfully by flake8 (no issues).")
                file_detail["linter_status"] = "success"
                file_detail["linter_output"] = lint_stdout + lint_stderr

            build_results["details"].append(file_detail)

        ctx["build_results"] = build_results
        if build_results["status"] == "failure":
            logging.info(f"[{self.name}] Build failed. Details: {build_results['details']}")
            # Optionally stop the pipeline
            # raise RuntimeError(f"[{self.name}] Build failed.")
        else:
            logging.info(f"[{self.name}] Build completed. Status: {build_results['status']}")

        return ctx
