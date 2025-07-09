from pathlib import Path
import subprocess
import logging

from apr_core.stages.stage import Stage, ResultStatus
from apr_core.util.util import get_local_workspace


class Test(Stage):
    name = "test"

    def run(self, context):
        logging.info(f"[{self.name}] running tests for fixed files")
        
        fixed_files = context.get("files", {}).get("fixed_files", [])

        test_cmd = context.get("config", {}).get("test_cmd")
        if not test_cmd:
            logging.info(f"[{self.name}] No test_cmd provided in config. Skipping tests.")
            self.set_result(ResultStatus.SKIPPED, "No test_cmd in config.")
            return context

        test_details = {}
        overall_success = True
        files_without_specific_tests = []

        # try specific tests for each file
        for file_path_str in fixed_files:
            file_path = Path(file_path_str)
            result = self._test_single_file(file_path, context)
            test_details[file_path_str] = result
            
            if result["status"] == "no_specific_test":
                files_without_specific_tests.append(file_path_str)
            elif result["status"] == "failure":
                overall_success = False

        # Second pass: if there are files without specific tests, run general test once
        if files_without_specific_tests:
            general_test_result = self._run_test_command(test_cmd, timeout=60)
            
            # Apply general test result to all files that didn't have specific tests
            for file_path_str in files_without_specific_tests:
                test_details[file_path_str] = {
                    "status": "success" if general_test_result["success"] else "failure",
                    "details": {
                        "test_type": "general",
                        "test_command": test_cmd,
                        "stdout": general_test_result["stdout"],
                        "stderr": general_test_result["stderr"]
                    }
                }
                
                if not general_test_result["success"]:
                    overall_success = False

        self._finalize_test_results(overall_success, test_details)
        context["state"]["repair_successful"] = overall_success
        return context

    def _test_single_file(self, file_path: Path, context: dict) -> dict:
        """Test a single file, return structured result."""
        file_name = file_path.stem
        logging.info(f"[{self.name}] Testing {file_name}...")

        # For QuixBugs: look for specific test file
        test_file = f"test_{file_name}.py"
        test_dir = context.get("config", {}).get("workdir", ".").replace("python_programs", "python_testcases")
        test_path = Path(get_local_workspace()) / test_dir / test_file

        logging.info(f"[{self.name}] Looking for specific test: {test_path}")

        if test_path.exists():
            # Build command for specific test
            parent_dir = test_path.parent.parent
            cmd = f"cd {parent_dir} && python -m pytest {test_path.relative_to(parent_dir)} -v"
            
            test_result = self._run_test_command(cmd, timeout=30)
            
            if test_result["success"]:
                logging.info(f"[{self.name}] Specific test passed for {file_name}.")
            else:
                logging.info(f"[{self.name}] Specific test failed for {file_name}.")
                
            return {
                "status": "success" if test_result["success"] else "failure",
                "details": {
                    "test_type": "specific",
                    "test_command": cmd,
                    "stdout": test_result["stdout"],
                    "stderr": test_result["stderr"]
                }
            }
        else:
            logging.info(f"[{self.name}] No specific test file found for {file_name}.")
            return {
                "status": "no_specific_test",
                "details": {
                    "test_type": "none",
                    "test_command": "N/A - no specific test found",
                    "stdout": "",
                    "stderr": ""
                }
            }

    def _run_test_command(self, command: str, timeout: int = 60) -> dict:
        """Run a test command and return structured result."""
        logging.info(f"[{self.name}] Executing test command: {command}")
        try:
            process = subprocess.run(
                command, 
                shell=True,
                capture_output=True, 
                text=True, 
                check=False,
                timeout=timeout
            )
            return {
                "success": process.returncode == 0,
                "stdout": process.stdout,
                "stderr": process.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": f"Test timed out after {timeout} seconds",
                "stderr": "Execution took too long"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Error running command: {str(e)}"
            }

    def _finalize_test_results(self, overall_success: bool, test_details: dict) -> None:
        """Finalize test results and set appropriate stage result."""
        
        if not overall_success:
            failed_tests = [fp for fp, data in test_details.items() 
                          if data["status"] == "failure"]
            message = f"Tests failed. {len(failed_tests)} files with test failures."
            logging.error(f"[{self.name}] {message}")
            self.set_result(ResultStatus.FAILURE, message, test_details)
        else:
            message = f"All tests passed for {len(test_details)} files."
            logging.info(f"[{self.name}] {message}")
            self.set_result(ResultStatus.SUCCESS, message, test_details)
