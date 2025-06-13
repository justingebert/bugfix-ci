import time
import logging
from enum import Enum
from typing import Optional, Any


class ResultStatus(Enum):
    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    SKIPPED = "skipped"

class Stage:
    name = "base"

    def __init__(self):
        self.results = {
            "status": ResultStatus.UNKNOWN.value,
            "message": "",
            "details": {}
        }

    def set_result(self, status: ResultStatus, message: str, details: Optional[dict[str, Any]] = None):
        self.results = {
            "status": status.value,
            "message": message,
            "details": details or {}
        }

    def run(self, context):
        raise NotImplementedError
    
    def execute(self, context, retry = False) -> tuple[bool, dict]:
        """Execute the stage with timing, metrics and error handling
        Args:
            context (dict): The context dictionary containing state, history and configuration.
            retry (bool): Whether to retry the stage on failure. Defaults to False. -> appends stage to last attempt
        Returns:
            - dict: The updated context dictionary.
        """
        stage_start_time = time.monotonic()
        attempt = context["state"].get("current_attempt", 0)
        stage_key = f"{self.name}_attempt_{attempt}"

        try:
            logging.info(f"== Running stage: {self.name} ==")
            context["state"]["current_stage"] = self.name
            context = self.run(context)
            stage_end_time = time.monotonic()
            stage_duration = stage_end_time - stage_start_time

            context["stages"][stage_key] = {
                "results": self.results,
                "duration": round(stage_duration, 4),
            }
            
            if retry and attempt > 0 and context.get("attempts"):
                context["attempts"][-1]["stages"][self.name] = self.results
            
            context["metrics"]["execution_repair_stages"][stage_key] = round(stage_duration, 4)
            logging.info(f"== Stage {self.name} completed in {stage_duration:.4f} seconds ==")

            return context
            
        except Exception as e:
            stage_duration = time.monotonic() - stage_start_time
            raise RuntimeError(f"!! Stage {self.name} failed after {stage_duration:.4f} seconds: {e}", exc_info=True)