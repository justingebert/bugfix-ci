import pathlib, datetime
from agent_core.stage import Stage, ResultStatus
from agent_core.tools.local_repo_tools import run_command
import logging


class Build(Stage):
    name = "build"

    def run(self, context):
        logging.info(f"[{self.name}] starting build process 👷")
        
        fixed_files = context.get("files", {}).get("fixed_files", [])
        if not fixed_files:
            logging.info(f"[{self.name}] No fixed files found to build.")
            self.set_result(ResultStatus.SKIPPED, "No fixed files to build.")
            return context

        build_details = {}
        overall_success = True

        for file_path_str in fixed_files:
            file_path = pathlib.Path(file_path_str)
            build_details[file_path_str] = self._process_file(file_path)
            
            file_status = build_details[file_path_str]["status"]
            if file_status in ["error", "issues_found"]:
                overall_success = False

        self._finalize_build_results(overall_success, build_details)
        context["state"]["repair_successful"] = overall_success
        return context

    def _process_file(self, file_path: pathlib.Path) -> dict:
        """Process a single file with formatting and linting, return structured result."""
        
        formatter_result = self._format_file(file_path)
        linter_result = self._lint_file(file_path)
        
        if formatter_result["status"] == "error" or linter_result["status"] == "error":
            file_status = "error"
        elif linter_result["status"] == "issues_found":
            file_status = "issues_found"
        else:
            file_status = "success"

        return {
            "status": file_status,
            "details": {
                "formatter": formatter_result,
                "linter": linter_result
            }
        }

    def _format_file(self, file_path: pathlib.Path) -> dict:
        """Format a file with black and return structured result."""
        logging.info(f"[{self.name}] Formatting {file_path} with black...")
        format_success, format_stdout, format_stderr = run_command(["python", "-m", "black"], file_path)
        
        if not format_success:
            if "Command not found" in format_stderr or "Error running command" in format_stderr:
                logging.error(f"[{self.name}] Error running black on {file_path}: {format_stderr}")
                return {
                    "status": "error",
                    "output": format_stderr
                }
            else:
                logging.info(f"[{self.name}] black ran on {file_path}. Output: {format_stdout} {format_stderr}")
                return {
                    "status": "success",
                    "output": f"stdout: {format_stdout}\nstderr: {format_stderr}"
                }
        else:
            logging.info(f"[{self.name}] {file_path} formatted successfully by black.")
            return {
                "status": "success",
                "output": format_stdout + format_stderr
            }

    def _lint_file(self, file_path: pathlib.Path) -> dict:
        """Lint a file with flake8 and return structured result."""
        logging.info(f"[{self.name}] Linting {file_path} with flake8...")
        lint_success, lint_stdout, lint_stderr = run_command(["python", "-m", "flake8"], file_path)

        if "Command not found" in lint_stderr or "Error running command" in lint_stderr:
            logging.error(f"[{self.name}] Error running flake8 on {file_path}: {lint_stderr}")
            return {
                "status": "error",
                "output": lint_stderr
            }
        elif not lint_success:
            logging.warning(f"[{self.name}] flake8 found issues in {file_path}:\n{lint_stdout}{lint_stderr}")
            return {
                "status": "issues_found",
                "output": lint_stdout + lint_stderr
            }
        else:
            logging.info(f"[{self.name}] {file_path} linted successfully by flake8 (no issues).")
            return {
                "status": "success",
                "output": lint_stdout + lint_stderr
            }

    def _finalize_build_results(self, overall_success: bool, build_details: dict) -> None:
        """Finalize build results and set appropriate stage result."""

        if not overall_success:
            failed_files = [fp for fp, data in build_details.items() 
                          if data["status"] in ["error", "issues_found"]]
            message = f"Build failed. {len(failed_files)} files with issues."
            logging.error(f"[{self.name}] {message}")
            self.set_result(ResultStatus.FAILURE, message, build_details)
        else:
            message = f"Build completed successfully for {len(build_details)} files."
            logging.info(f"[{self.name}] {message}")
            self.set_result(ResultStatus.SUCCESS, message, build_details)
