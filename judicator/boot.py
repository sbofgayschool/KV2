# -*- encoding: utf-8 -*-

__author__ = "chenty"

# Add current folder and parent folder (when testing) into python path
import os
os.environ["PYTHONPATH"] += ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())

from jsoncomment import JsonComment
json = JsonComment()
import time
import fcntl

from utility.function import get_logger


if __name__ == "__main__":
    # TODO: Read arguments from the command line

    # Load configuration
    with open("config/boot.json", "r") as f:
        config = json.load(f)

    # Generate a logger
    if "log" in config:
        logger = get_logger(
            "main",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("boot", None, None)

    services = {"etcd": {}, "mongodb": {}, "main": {}}
    # TODO: Load and modify configuration of etcd, mongodb and main

    # Generate pid files for service daemons
    for s in services:
        with open(services[s]["pid_file"], "w") as f:
            f.write("-1")

    # Check whether service daemons are running regularly
    while True:
        for s in services:
            logger.info("Checking status of service %s." % s)
            # Try to open the pid file
            try:
                with open(services[s]["pid_file"], "r+") as file:
                    # If opened successfully, try to get a lock
                    # TODO: Lock the file
                    # If the lock is obtained, do the regular check up for the service and start it, if required
                    try:
                        # TODO: Check the status of each services and start them, if required
                        pass
                    except:
                        logger.error("Exception occurs when checking service %s." % s, exc_info=True)
                    finally:
                        # The lock must be released
                        # TODO: Release the lock
                        pass
            except OSError as e:
                # TODO: Figure out the value of EACCES and EAGAIN
                if e.errno == 1:
                    # If OSError occur and errno equals EACCES or EAGAIN, this means the lock can not be obtained
                    # Then, do nothing
                    # This could happen when the service is being maintained
                    pass
                else:
                    raise
            except:
                logger.error("Fatal exception occurs when checking service %s." % s, exc_info=True)

        time.sleep(config["check_interval"])
