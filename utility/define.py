# -*- encoding: utf-8 -*-

__author__ = "chenty"


RETURN_CODE = {
    "OK": 0,
    "ERROR": -1
}

TASK_STATUS = {
    "PENDING": 0,
    "COMPILING": 1,
    "COMPILE_FAILED": 2,
    "RUNNING": 3,
    "RUN_FAILED": 4,
    "SUCCESS": 5,
    "RETRYING": 6,
    "CANCEL": 7
}