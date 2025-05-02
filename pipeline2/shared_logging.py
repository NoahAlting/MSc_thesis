import logging
import os

def setup_logging(log_file, append=False, clear=True):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    if clear and os.path.exists(log_file):
        open(log_file, 'w').close()  # Clear contents first

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    mode = 'a' if append else 'w'
    handler = logging.FileHandler(log_file, mode=mode)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if append:
        logger.info("=" * 60)
        logger.info("NEW SESSION STARTED")


def setup_module_logger(name: str, data_dir: str) -> logging.Logger:
    """
    Sets up an isolated file logger for a given module, writing to data_dir/logs/<name>.log.
    Prevents logs from leaking into parent loggers like 'main'.

    Parameters:
    - name (str): e.g. 'preprocess', 'segmentation', 'merge'
    - data_dir (str): the folder where logs/ will be created

    Returns:
    - logger (logging.Logger): a ready-to-use logger instance
    """
    log_dir = os.path.join(data_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{name}.log")

    logger = logging.getLogger(f"pipeline.{name}")
    logger.propagate = False

    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path) for h in logger.handlers):
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
