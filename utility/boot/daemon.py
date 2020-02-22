# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json_comment = JsonComment()
import json
import argparse
import docker
import filelock
import signal
import subprocess
import time
import os

from utility.function import get_logger


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

def run(service_list, module_name, module_description, conf_path="config/templates/boot.json"):
    """
    Parse args and start services with routine checks
    :param service_list: List of all services in the starting order
    :param module_name: The name of the running module
    :param module_description: The description of the module
    :param conf_path: Path to boot config
    :return: None
    """
    # Get a parser and add common args
    parser = argparse.ArgumentParser(description=module_description)
    parser.add_argument("--docker-sock", dest="docker_sock", default=None,
                        help="Path to mapped docker sock file")
    parser.add_argument("--retry-times", type=int, dest="retry_times", default=None,
                        help="Total retry time of key operations")
    parser.add_argument("--retry-interval", type=int, dest="retry_interval", default=None,
                        help="Interval between retries of key operations")

    parser.add_argument("--boot-check-interval", type=int, dest="boot_check_interval", default=None,
                        help="Interval between services check in boot module")
    parser.add_argument("--boot-print-log", dest="boot_print_log", action="store_const", const=True, default=False,
                        help="Print the log of boot module to stdout")

    # Add args for services
    for s in service_list:
        s["generator"] = s["args_parser"](parser, *s.get("args", tuple()), **s.get("kwargs", {}))

    # Parse args
    args = parser.parse_args()

    # Load configuration
    with open(conf_path, "r") as f:
        config = json_comment.load(f)
    if args.boot_check_interval is not None:
        config["check_interval"] = args.boot_check_interval
    if args.boot_print_log:
        config.pop("log", None)

    # Generate logger
    if "log" in config:
        logger = get_logger("boot", config["log"]["info"], config["log"]["error"])
    else:
        logger = get_logger("boot", None, None)
    logger.info("%s boot program started." % module_name)

    # If docker-sock is given, generate a docker client for it
    client = docker.APIClient(base_url=args.docker_sock) if args.docker_sock else None
    # Dictionary for services
    services = {}
    # Start order of services
    start_order = []

    # Load and modify config for all services by calling config generator
    for s in service_list:
        # Load config template
        with open(s["config_template"], "r") as f:
            config_sub = json_comment.load(f)
        # Modify services config
        s["generator"](args, config_sub, client, services, start_order)
        # Write config
        with open(s["config"], "w") as f:
            f.write(json.dumps(config_sub, indent=4))
        logger.info("Service %s configuration loaded." % s["name"])

    # Check whether service daemons are running regularly
    try:
        while True:
            for s in start_order:
                logger.info("Checking status of service %s." % s)
                # Try to open the pid file of the service
                try:
                    # Lock the pid file
                    with filelock.FileLock(services[s]["pid_file"] + ".lock", timeout=0):
                        logger.debug("Locked pid file %s." % services[s]["pid_file"])

                        # If the process is None or the process has exited, (re)start it and rewrite the pid file
                        if (not services[s]["process"]) or services[s]["process"].poll() is not None:
                            logger.warning("Service %s is down." % s)
                            # Start the service and write the pid file
                            with open(services[s]["pid_file"], "w") as f:
                                logger.info("Starting the service %s and writing pid file." % s)
                                services[s]["process"] = subprocess.Popen(services[s]["command"])
                                f.write(str(services[s]["process"].pid))
                        else:
                            logger.info("Service %s is running." % s)
                    logger.debug("Unlocked pid file %s." % services[s]["pid_file"])
                except KeyboardInterrupt:
                    raise
                except filelock.Timeout:
                    logger.warning("Failed to obtain lock for service %s. Skipping check." % s, exc_info=True)
                except:
                    logger.error("Failed to check status for service %s." % s, exc_info=True)

            time.sleep(config["check_interval"])

    except KeyboardInterrupt:
        logger.info("Received SIGINT. Stopping service check.", exc_info=True)

    # Clean all services
    for s in start_order[: : -1]:
        if services[s]["process"]:
            os.kill(services[s]["process"].pid, signal.SIGINT)
            logger.info("Killing service %s." % s)
            services[s]["process"].wait()
            logger.info("Killed Service %s." % s)

    logger.info("%s boot program exiting." % module_name)
    return
