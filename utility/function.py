# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
import logging, logging.handlers
import time


# Format for normal logger.
LOG_FORMAT = "%(name)s - %(asctime)s %(levelname)s - %(message)s"
# Format for raw output logger.
RAW_FORMAT = "%(name)s - %(message)s"

def get_logger(name, info_file, error_file, raw=False):
    # Generate logger object
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Config info level logger handler.
    if info_file:
        info_handler = logging.handlers.TimedRotatingFileHandler(info_file, when='midnight', interval=1)
    else:
        info_handler = logging.StreamHandler()
    info_handler.setLevel(logging.DEBUG)
    info_handler.setFormatter(logging.Formatter(RAW_FORMAT if raw else LOG_FORMAT))

    # Config error level logger handler.
    if error_file:
        error_handler = logging.FileHandler(error_file)
    else:
        error_handler = logging.StreamHandler()
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(RAW_FORMAT if raw else LOG_FORMAT))

    # Add handler to logger.
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    return logger

def check_empty_dir(path):
    return len(os.listdir(path)) == 0

def try_with_times(times, interval, logger, tag, func, *args, **kwargs):
    logger.info("Trying to " + tag + " with %d chances." % times)
    while times > 0:
        time.sleep(interval)
        try:
            res = func(*args, **kwargs)
            logger.info(tag + " succeeded.")
            return True, res
        except:
            times -= 1
            logger.warn("Failed to " + tag + ", %d more chances." % times, exc_info=True)
    logger.error(tag + " failed.")
    return False, None
