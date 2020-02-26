# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2020 SBofGaySchoolBuPaAnything
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

__author__ = "chenty"

import zlib
import bson
import re


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

def transform_id(f):
    """
    Transform the _id (ObjectId) field to a id field (String) inside a json
    :param f: The json object
    :return: None
    """
    f["id"] = str(f["_id"])
    del f["_id"]
    return


def check_task_dict_size(task):
    """
    Check whether a task dictionary is larger than the limitation
    :param task: The task dictionary
    :return: The result
    """
    return len(bson.BSON.encode(task)) < TASK_DICTIONARY_MAX_SIZE

def check_id(id):
    """
    Check whether a id is valid
    :param id: The id
    :return: The result
    """
    return bool(re.match(r"^[a-f0-9]{24}$", id))

def check_int(x):
    """
    Check whether a int is valid
    :param x: The int
    :return: The result
    """
    return 0 <= x <= 2147483647

def decompress_and_truncate(zipped, truncate=True, max_length=1000):
    """
    Decompress a string zipped by zlib and truncate it
    :param zipped: Zipped string
    :param truncate: If it result be truncated
    :param max_length: Specified length
    :return:
    """
    res = zlib.decompress(zipped).decode("utf-8") if zipped else ""
    if truncate and len(res) > max_length:
        res = res[: max_length] + "..."
    return res
