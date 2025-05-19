import time
import logging

class Stage:
    name = "base"
    def run(self, ctx):
        raise NotImplementedError

    def execute(self, ctx):
        """Execute the stage with timing, metrics and error handling"""
        stage_start_time = time.monotonic()
        attempt = ctx["metrics"].get("current_attempt", 0)
        stage_key = f"{self.name}" if attempt == 0 else f"{self.name}_attempt_{attempt}"

        try:
            logging.info(f"== Running stage: {self.name} ==")
            new_ctx = self.run(ctx)
            stage_end_time = time.monotonic()
            stage_duration = stage_end_time - stage_start_time

            # Store metrics
            ctx["metrics"]["execution_times_stages"][stage_key] = round(stage_duration, 4)
            logging.info(f"== Stage {self.name} completed in {stage_duration:.4f} seconds ==")

            return True, new_ctx
        except Exception as e:
            stage_end_time = time.monotonic()
            stage_duration = stage_end_time - stage_start_time

            # Store metrics
            ctx["metrics"]["execution_times_stages"][stage_key] = round(stage_duration, 4)
            logging.error(f"!! Stage {self.name} failed after {stage_duration:.4f} seconds: {e}", exc_info=True)

            return False, ctx