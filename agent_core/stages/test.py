import pathlib
import subprocess
import logging

from agent_core.stage import Stage
from agent_core.util.util import get_local_workspace

class Test(Stage):
    name = "test"

    def run(self, ctx):
        logging.info(f"[{self.name}] running tests for fixed files")
        fixed_files = ctx.get("fixed_files", [])
        if not fixed_files:
            logging.info(f"[{self.name}] No fixed files found to test.")
            ctx["test_results"] = {"status": "skipped", "message": "No fixed files"}
            return ctx

        test_cmd = ctx.get("cfg", {}).get("test_cmd")
        if not test_cmd:
            logging.info(f"[{self.name}] No test_cmd provided in config. Skipping tests.")
            ctx["test_results"] = {"status": "skipped", "message": "No test_cmd in config"}
            return ctx

        test_results = {"status": "success", "details": []}

        for file_path_str in fixed_files:
            file_path = pathlib.Path(file_path_str)
            file_name = file_path.stem

            logging.info(f"[{self.name}] Testing {file_name}...")

            # For QuixBugs: run the specific test for this file
            test_file = f"test_{file_name}.py"
            test_dir = ctx.get("cfg", {}).get("workdir", ".").replace("python_programs", "python_testcases")
            test_path = get_local_workspace() / test_dir / test_file

            test_detail = {"file": str(file_path)}

            logging.info(f"[{self.name}] trying {test_path}...")

            if test_path.exists():
                logging.info(f"[{self.name}] Running specific test: {test_path}")
                try:
                    parent_dir = test_path.parent.parent

                    cmd = [
                        "cd", str(parent_dir), "&&",
                        "python", "-m", "pytest",
                        str(test_path.relative_to(parent_dir)), "-v"
                    ]
                    logging.info(f"[{self.name}] Executing command: {' '.join(cmd)}")
                    process = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True, check=False,
                                             timeout=30)
                    success = process.returncode == 0
                    stdout = process.stdout
                    stderr = process.stderr
                except subprocess.TimeoutExpired:
                    success = False
                    stdout = "Test timed out after 30 seconds"
                    stderr = "Execution took too long"
                except Exception as e:
                    success = False
                    stdout = ""
                    stderr = f"Error running test: {str(e)}"
            else:
                logging.info(f"[{self.name}] No specific test file found. Running general tests.")
                try:
                    cmd = test_cmd.split()
                    logging.info(f"[{self.name}] Executing command: {' '.join(cmd)}")
                    process = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
                    success = process.returncode == 0
                    stdout = process.stdout
                    stderr = process.stderr
                except subprocess.TimeoutExpired:
                    success = False
                    stdout = "Test timed out after 30 seconds"
                    stderr = "Execution took too long"
                except Exception as e:
                    success = False
                    stdout = ""
                    stderr = f"Error running command {' '.join(cmd)}: {str(e)}"

            test_detail.update({
                "test_command": str(test_path) if test_path.exists() else " ".join(cmd),
                "status": "success" if success else "failure",
                "stdout": stdout,
                "stderr": stderr
            })

            if not success:
                test_results["status"] = "failure"
                logging.info(f"[{self.name}] Tests failed for {file_name}.")
                logging.info(f"[{self.name}] stdout: {stdout}")
                logging.info(f"[{self.name}] stderr: {stderr}")
            else:
                logging.info(f"[{self.name}] Tests passed for {file_name}.")

            test_results["details"].append(test_detail)

        ctx["test_results"] = test_results
        return ctx
