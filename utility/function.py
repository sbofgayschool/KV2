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

import os
import logging, logging.handlers
import time
import netifaces
import socket


# Format for normal logger.
LOG_FORMAT = "%(name)s - %(asctime)s %(levelname)s - %(message)s"
# Format for raw output logger.
RAW_FORMAT = "%(name)s - %(message)s"

def get_logger(name, info_file, error_file, raw=False):
    """
    Get a logger forwarding message to designated places
    :param name: The name of the logger
    :param info_file: File to log information less severe than error
    :param error_file: File to log error and fatal
    :param raw: If the output should be log in raw format
    :return: Generated logger
    """
    # Generate or get the logger object
    if isinstance(name, str):
        logger = logging.getLogger(name)
    else:
        logger = name
    logger.setLevel(logging.DEBUG)

    # Config info level logger handler
    # If the file argument is None, forward the log to standard output
    if info_file:
        info_handler = logging.handlers.TimedRotatingFileHandler(info_file, when='midnight', interval=1)
    else:
        info_handler = logging.StreamHandler()
    info_handler.setLevel(logging.DEBUG)
    info_handler.setFormatter(logging.Formatter(RAW_FORMAT if raw else LOG_FORMAT))

    # Config error level logger handler
    if error_file:
        error_handler = logging.FileHandler(error_file)
    else:
        error_handler = logging.StreamHandler()
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(RAW_FORMAT if raw else LOG_FORMAT))

    # Add handlers to loggers
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    return logger

def log_output(logger, output, bit):
    """
    Log output from a stream until eof
    :param logger: The logger
    :param output: Output stream
    :param bit: Specified bit indicating the level of the message
    :return: None
    """
    while True:
        # Read
        message = output.readline()
        if not message:
            break

        # Judge the level of the information by the bit
        try:
            message = message[: -1].decode(encoding="utf-8")
            if bit is None:
                error = False
            else:
                error = message[bit] == 'E' or message[bit] == 'F' or message[bit] == 'C'
        except:
            error = True

        # Log the message
        if not error:
            logger.info(message)
        else:
            logger.error(message)
    return

def check_empty_dir(path):
    """
    Check if a dir is empty
    :param path: Path of the dir
    :return: If it is empty
    """
    return len(os.listdir(path)) == 0

def try_with_times(times, interval, sleep_first, logger, tag, func, *args, **kwargs):
    """
    Try a function with certain chances and retry intervals
    :param times: Amount of chances
    :param interval: Interval between retries
    :param logger: Logger to log information
    :param tag: Tag of the task, used only by logger
    :param func: Function to execute
    :param sleep_first: If sleep should be called before the first try
    :param args: Args for the function
    :param kwargs: keyword args for the function
    :return: Tuple, (If the try is success, return value of the function (None if the try failed))
    """
    logger.info("Trying to %s with %d chances." % (tag, times))
    # Sleep before the first try if required
    if sleep_first:
        time.sleep(interval)
    while times > 0:
        try:
            # Try to run the function and return when no exceptions
            res = func(*args, **kwargs)
            logger.info("Operation %s succeeded." % tag)
            return True, res
        except:
            times -= 1
            # Log the info of the exception
            logger.warning("Failed to %s, %d more chances." % (tag, times), exc_info=True)
        if times > 0:
            time.sleep(interval)

    logger.error("Operation %s failed." % tag)
    # Return when finally failed.
    return False, None

def transform_address(addr, docker_client):
    """
    Transform a string to valid address
    :param addr: The original address
    :param docker_client: The docker API client
    :return: Valid address
    """
    # If the address is not all upper letters, indicating it is a address
    if not addr.isupper():
        return addr
    # If it is DOCKER, get the name of the docker container
    # Else if it is ALL, return 0.0.0.0
    # Else, it is a name of a net interface card, return the address of it
    if addr == "DOCKER":
        return docker_client.inspect_container(socket.gethostname())["Name"][1:]
    elif addr == "ALL":
        return "0.0.0.0"
    return netifaces.ifaddresses(addr.lower())[netifaces.AF_INET][0]["addr"]
