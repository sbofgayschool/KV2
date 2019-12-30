# -*- encoding: utf-8 -*-

__author__ = "chenty"

# Add current folder and parent folder (when testing) into python path
import os
os.environ["PYTHONPATH"] += ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())

from jsoncomment import JsonComment
json_comment = JsonComment()

import json
import time
import fcntl
import errno
import subprocess

from utility.function import get_logger


if __name__ == "__main__":
    # TODO: Read arguments from the command line

    # Load configuration
    with open("config/templates/boot.json", "r") as f:
        config = json_comment.load(f)

    # Generate a logger
    if "log" in config:
        logger = get_logger(
            "main",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("boot", None, None)

    services = {}
    # TODO: Modify configuration of etcd and main
    with open("config/templates/etcd.json", "r") as f:
        config_sub = json_comment.load(f)
    with open("config/etcd.json", "w") as f:
        f.write(json.dumps(config_sub))
    services["etcd"] = {
        "pid_file": config_sub["daemon"]["pid_file"],
        "command": config_sub["daemon"]["exe"],
        "process": None
    }

    """
    with open("config/templates/main.json", "r") as f:
        config_sub = json_comment.load(f)
    with open("config/main.json", "w") as f:
        f.write(json.dumps(config_sub))
    services["main"] = {
        "pid_file": config_sub["pid_file"],
        "command": config_sub["exe"],
        "process": None
    }
    """

    # Generate pid files for service daemons
    for s in services:
        with open(services[s]["pid_file"], "w") as f:
            f.write("-1")

    # Check whether service daemons are running regularly
    while True:
        for s in services:
            logger.info("Checking status of service %s." % s)
            # Try to open the pid file of the service
            try:
                with open(services[s]["pid_file"], "r+") as f:
                    # If opened successfully (this should always happen), try to get a lock
                    fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logger.debug("Pid file %s locked successfully." % services[s]["pid_file"])

                    # If the lock is obtained, do the regular check up for the service and start it, if required
                    try:
                        # If the process is None or the process has exited, restart it and rewrite the pid file
                        if (not services[s]["process"]) or services[s]["process"].poll() is not None:
                            logger.warning("Service %s is down. Trying to start the service and write pid file." % s)
                            services[s]["process"] = subprocess.Popen(services[s]["command"])
                            f.truncate()
                            f.write(str(services[s]["process"].pid))
                        else:
                            logger.info("Service %s is running." % s)
                    except:
                        logger.error("Exception occurs when checking service %s." % s, exc_info=True)
                    finally:
                        # The lock must be released
                        fcntl.lockf(f, fcntl.LOCK_UN)
                        logger.debug("Pid file %s unlocked successfully." % services[s]["pid_file"])
            except OSError as e:
                if e.errno == errno.EACCES or e.errno == errno.EAGAIN:
                    # If OSError occur and errno equals EACCES or EAGAIN, this means the lock can not be obtained
                    # Then, do nothing
                    # This could happen when the service is being maintained
                    logger.warning("Failed to obtain lock for %s, skip corresponding service check." % s)
                else:
                    raise e
            except:
                logger.error("Fatal exception occurs when checking service %s." % s, exc_info=True)

        time.sleep(config["check_interval"])
