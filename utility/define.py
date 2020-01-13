# -*- encoding: utf-8 -*-

__author__ = "chenty"


# Format for normal logger.
LOG_FORMAT = "%(name)s - %(asctime)s %(levelname)s - %(message)s"
# Format for raw output logger.
RAW_FORMAT = "%(name)s - %(message)s"

# Status of a task
TASK_STATUS = {
    "PENDING": 0,
    "COMPILING": 1,
    "COMPILE_FAILED": 2,
    "RUNNING": 3,
    "RUN_FAILED": 4,
    "SUCCESS": 5,
    "RETRYING": 6,
    "CANCELLED": 7,
    "UNKNOWN_ERROR": 8
}

# Max size of a task dictionary
TASK_DICTIONARY_MAX_SIZE = 16252928
