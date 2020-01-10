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
import argparse
import socket
import signal
import docker

from utility.function import get_logger, transform_address


def handler(signum, frame):
    """
    Signal handler of SIGTERM. Sending SIGINT to this process
    :param signum: Unused, signal number
    :param frame: Unused
    :return: None
    """
    logger.info("Received SIGTERM. Sending SIGINT to self.")
    # Send signal
    os.kill(os.getpid(), signal.SIGINT)
    return

# Register a signal for cleanup
signal.signal(signal.SIGTERM, handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gateway of Khala system. Provide HTTP API interface and a website.')
    parser.add_argument("--docker-sock", dest="docker_sock", default=None)
    parser.add_argument("--retry-times", type=int, dest="retry_times", default=None)
    parser.add_argument("--retry-interval", type=int, dest="retry_interval", default=None)

    parser.add_argument("--boot-check-interval", type=int, dest="boot_check_interval", default=None)
    parser.add_argument("--boot-print-log", dest="boot_print_log", action="store_const", const=True, default=False)

    parser.add_argument("--etcd-exe", dest="etcd_exe", default=None)
    parser.add_argument("--etcd-name", dest="etcd_name", default=None)
    parser.add_argument("--etcd-peer-port", type=int, dest="etcd_peer_port", default=None)
    parser.add_argument("--etcd-client-port", type=int, dest="etcd_client_port", default=None)
    parser.add_argument("--etcd-cluster-init-discovery", dest="etcd_cluster_init_discovery", default=None)
    parser.add_argument("--etcd-cluster-join-member", dest="etcd_cluster_join_member", default=None)
    parser.add_argument("--etcd-print-log", dest="etcd_print_log", action="store_const", const=True, default=False)

    parser.add_argument("--uwsgi-host", dest="uwsgi_host", default=None)
    parser.add_argument("--uwsgi-port", dest="uwsgi_port", default=None)
    parser.add_argument("--uwsgi-process", type=int, dest="uwsgi_process", default=None)
    parser.add_argument("--uwsgi-print-log", dest="uwsgi_print_log", action="store_const", const=True, default=False)

    args = parser.parse_args()

    # Load configuration
    with open("config/templates/boot.json", "r") as f:
        config = json_comment.load(f)
    if args.boot_check_interval is not None:
        config["check_interval"] = args.boot_check_interval
    if args.boot_print_log:
        config.pop("log", None)

    # Generate a logger
    if "log" in config:
        logger = get_logger(
            "main",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("boot", None, None)
    logger.info("Gateway boot program started.")

    # If docker-sock is given, generate a docker client for it
    client = docker.APIClient(base_url=args.docker_sock) if args.docker_sock else None

    # Generate services
    services = {}

    # Load and modify config for etcd
    with open("config/templates/etcd.json", "r") as f:
        config_sub = json_comment.load(f)

    if args.retry_times is not None:
        config_sub["daemon"]["retry"]["times"] = args.retry_times
    if args.retry_interval is not None:
        config_sub["daemon"]["retry"]["interval"] = args.retry_interval
    if args.etcd_exe is not None:
        config_sub["etcd"]["exe"] = args.etcd_exe
    if args.etcd_name is not None:
        config_sub["etcd"]["name"] = args.etcd_name
    if args.etcd_peer_port is not None:
        config_sub["etcd"]["listen"]["peer_port"] = str(args.etcd_peer_port)
        config_sub["etcd"]["advertise"]["peer_port"] = str(args.etcd_peer_port)
    if args.etcd_client_port is not None:
        config_sub["etcd"]["listen"]["client_port"] = str(args.etcd_client_port)
        config_sub["etcd"]["advertise"]["client_port"] = str(args.etcd_client_port)
    if args.etcd_cluster_init_discovery is not None:
        config_sub["etcd"]["cluster"] = {"type": "init", "discovery": args.etcd_cluster_init_discovery}
    if args.etcd_cluster_join_member is not None:
        config_sub["etcd"]["cluster"] = {"type": "join", "member": args.etcd_cluster_join_member}
    if args.etcd_print_log:
        config_sub["daemon"].pop("log_daemon", None)
        config_sub["daemon"].pop("log_etcd", None)
    if args.docker_sock is not None:
        config_sub["etcd"]["exe"] = "etcd"
        if args.etcd_name is None:
            config_sub["etcd"]["name"] = socket.gethostname()

    with open("config/etcd.json", "w") as f:
        f.write(json.dumps(config_sub))
    services["etcd"] = {
        "pid_file": config_sub["daemon"]["pid_file"],
        "command": config_sub["daemon"]["exe"],
        "process": None
    }

    # The same thing for uwsgi
    with open("config/templates/uwsgi.json", "r") as f:
        config_sub = json_comment.load(f)

    if args.uwsgi_host is not None:
        config_sub["uwsgi"]["host"] = transform_address(args.uwsgi_host, client)
    if args.uwsgi_port is not None:
        config_sub["uwsgi"]["port"] = str(args.uwsgi_port)
    if args.uwsgi_process is not None:
        config_sub["uwsgi"]["process"] = args.uwsgi_process
    if args.uwsgi_print_log:
        config_sub["daemon"].pop("log_daemon", None)
        config_sub["daemon"].pop("log_uwsgi", None)
        config_sub["server"].pop("log_daemon", None)

    with open("config/uwsgi.json", "w") as f:
        f.write(json.dumps(config_sub))
    services["uwsgi"] = {
        "pid_file": config_sub["daemon"]["pid_file"],
        "command": config_sub["daemon"]["exe"],
        "process": None
    }

    # Generate pid files for service daemons
    for s in services:
        with open(services[s]["pid_file"], "w") as f:
            f.write("-1")

    # Generate start and exit order list
    start_order = ["etcd", "uwsgi"]
    exit_order = start_order[: : -1]

    # Check whether service daemons are running regularly
    while True:
        try:
            for s in start_order:
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

        except KeyboardInterrupt:
            logger.info("Receiving SIGINT. Quiting the whole program.")
            break

    # Clean all services
    for s in exit_order:
        if services[s]["process"]:
            os.kill(services[s]["process"].pid, signal.SIGINT)
            logger.info("Killing service %s." % s)
            services[s]["process"].wait()
            logger.info("Service %s finished." % s)

    logger.info("Exiting.")
