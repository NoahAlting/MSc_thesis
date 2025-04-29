import logging
import os

def setup_logging(log_file, append=True, clear=False):
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
