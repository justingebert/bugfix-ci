import logging
import pathlib
from datetime import datetime

def create_log_dir():
    base_log_dir = pathlib.Path("/workspace/logs")
    base_log_dir.mkdir(exist_ok=True, parents=True)

    run_timestamp = datetime.now().strftime("%m_%d_%H_%M")
    log_dir = base_log_dir / f"run_at_{run_timestamp}"
    log_dir.mkdir(exist_ok=True)

    return log_dir

def setup_logging(name, log_dir):
    """Configure logging to write to both console and file"""
    log_file = log_dir / f"{name}.log"

    # Reset handlers (in case this function is called multiple times)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return log_file
