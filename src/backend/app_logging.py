import logging
import sys
import os


def setup_logging(log_file: str = "nodes.log", level: int = logging.INFO):
    """Configure logging for application."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    log_file_path = os.path.join(base_dir, log_file)

    root_logger = logging.getLogger()

    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
