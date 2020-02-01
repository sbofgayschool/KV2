# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
import fcntl
import errno
import subprocess
import signal
import time


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
