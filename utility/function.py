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

def log_output(logger, output, bit):
    while True:
        message = output.readline()
        if not message:
            break
        try:
            message = message[: -1].decode(encoding="utf-8")
            error = message[bit] == 'E' or  message[bit] == 'F'
        except:
            error = True
        if not error:
            logger.info(message)
        else:
            logger.error(message)
    return

def check_empty_dir(path):
    return len(os.listdir(path)) == 0

def try_with_times(times, interval, logger, tag, func, *args, **kwargs):
    logger.info("Trying to %s with %d chances." % (tag, times))
    while times > 0:
        time.sleep(interval)
        try:
            res = func(*args, **kwargs)
            logger.info("Operation %s succeeded." % tag)
            return True, res
        except:
            times -= 1
            logger.warn("Failed to %s, %d more chances." % (tag, times), exc_info=True)
    logger.error("Operation %s failed." % tag)
    return False, None
