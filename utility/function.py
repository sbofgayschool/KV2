# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
import logging, logging.handlers
import time
import netifaces
import socket
import fcntl
import errno
import subprocess
import signal
import bson
import re

from utility.define import LOG_FORMAT, RAW_FORMAT, TASK_DICTIONARY_MAX_SIZE


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

def check_services(start_order, exit_order, services, check_interval, logger):
    """
    Check services regularly and maintain pid files
    :param start_order: A list indicating the start order of each service
    :param exit_order: A list indicating the terminate order of each service
    :param services: A dictionary with all service information
    :param check_interval: Interval between two checks
    :param logger: The logger
    :return: None
    """
    while True:
        try:
            for s in start_order:
                logger.info("Checking status of service %s." % s)
                # Try to open the pid file of the service
                try:
                    with open(services[s]["pid_file"], "r+") as f:
                        # If opened successfully (this should always happen), try to get a lock
                        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        logger.debug("Locked pid file %s." % services[s]["pid_file"])

                        # If the lock is obtained, do the regular check up for the service and start it, if required
                        try:
                            # If the process is None or the process has exited, restart it and rewrite the pid file
                            if (not services[s]["process"]) or services[s]["process"].poll() is not None:
                                logger.warning("Service %s is down." % s)
                                logger.info("Starting the service %s and writing pid file." % s)
                                services[s]["process"] = subprocess.Popen(services[s]["command"])
                                f.truncate()
                                f.write(str(services[s]["process"].pid))
                            else:
                                logger.info("Service %s is running." % s)
                        except:
                            logger.error("Failed to check service %s." % s, exc_info=True)
                        finally:
                            # The lock must be released
                            fcntl.lockf(f, fcntl.LOCK_UN)
                            logger.debug("Unlocked pid file %s." % services[s]["pid_file"])
                except OSError as e:
                    if e.errno == errno.EACCES or e.errno == errno.EAGAIN:
                        # If OSError occur and errno equals EACCES or EAGAIN, this means the lock can not be obtained
                        # Then, do nothing
                        # This could happen when the service is being maintained
                        logger.warning("Failed to obtain lock for %s. Skipped check." % s)
                    else:
                        raise e
                except:
                    logger.error("Failed to open pid file for service %s." % s, exc_info=True)
            time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("Received SIGINT. Stopping service check.")
            break

    # Clean all services
    for s in exit_order:
        if services[s]["process"]:
            os.kill(services[s]["process"].pid, signal.SIGINT)
            logger.info("Killing service %s." % s)
            services[s]["process"].wait()
            logger.info("Killed Service %s." % s)

    return

def sigterm_handler(signum, frame):
    """
    Signal handler of SIGTERM. Sending SIGINT to this process
    :param signum: Unused, signal number
    :param frame: Unused
    :return: None
    """
    # Send signal
    os.kill(os.getpid(), signal.SIGINT)
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
