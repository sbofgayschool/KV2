# -*- encoding: utf-8 -*-

__author__ = "chenty"

# Add current folder and parent folder (when testing) into python path
import os
os.environ["PYTHONPATH"] += ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())

from jsoncomment import JsonComment
json_comment = JsonComment()

import json
import argparse
import socket
import pwd
import grp
import signal

from utility.function import get_logger, check_services, sigterm_handler


# Register SIGTERM signal for cleanup
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    # Parse all arguments
    parser = argparse.ArgumentParser(description='Executor of Khala system. Execute tasks and report to judicators.')
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

    parser.add_argument("--etcd-exe", dest="etcd_exe", default=None,
                        help="Path to etcd executable file")
    parser.add_argument("--etcd-name", dest="etcd_name", default=None,
                        help="Name of the etcd node")
    parser.add_argument("--etcd-peer-port", type=int, dest="etcd_peer_port", default=None,
                        help="Listen peer port of the etcd node, default is 2000")
    parser.add_argument("--etcd-client-port", type=int, dest="etcd_client_port", default=None,
                        help="Listen client port of the etcd node, default is 2001")
    parser.add_argument("--etcd-cluster-init-discovery", dest="etcd_cluster_init_discovery", default=None,
                        help="Discovery token url of etcd node")
    parser.add_argument("--etcd-cluster-join-member-client", dest="etcd_cluster_join_member_client", default=None,
                        help="Client url of a member of the cluster which this etcd node is going to join")
    parser.add_argument("--etcd-print-log", dest="etcd_print_log", action="store_const", const=True, default=False,
                        help="Print the log of etcd module to stdout")

    parser.add_argument("--main-name", dest="main_name", default=None,
                        help="Name of the executor")
    parser.add_argument("--main-task-vacant", type=int, dest="main_task_vacant", default=None,
                        help="Capacity of tasks of the executor")
    parser.add_argument("--main-report-interval", type=int, dest="main_report_interval", default=None,
                        help="Interval between reports made to judicator from executor")
    parser.add_argument("--main-task-user-group", dest="main_task_user_group", default=None,
                        help="User:group string indicating execution user/group when executing real tasks.")
    parser.add_argument("--main-print-log", dest="main_print_log", action="store_const", const=True, default=False,
                        help="Print the log of main module to stdout")

    args = parser.parse_args()

    # Load configuration
    with open("config/templates/boot.json", "r") as f:
        config = json_comment.load(f)
    if args.boot_check_interval is not None:
        config["check_interval"] = args.boot_check_interval
    if args.boot_print_log:
        config.pop("log", None)

    # Generate logger
    if "log" in config:
        logger = get_logger(
            "boot",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("boot", None, None)
    logger.info("Executor boot program started.")

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
        if args.etcd_name == "ENV":
            config_sub["etcd"]["name"] = os.environ.get("NAME")
        else:
            config_sub["etcd"]["name"] = args.etcd_name
    if args.etcd_peer_port is not None:
        config_sub["etcd"]["listen"]["peer_port"] = str(args.etcd_peer_port)
        config_sub["etcd"]["advertise"]["peer_port"] = str(args.etcd_peer_port)
    if args.etcd_client_port is not None:
        config_sub["etcd"]["listen"]["client_port"] = str(args.etcd_client_port)
        config_sub["etcd"]["advertise"]["client_port"] = str(args.etcd_client_port)
    if args.etcd_cluster_init_discovery is not None:
        config_sub["etcd"]["cluster"] = {"type": "init", "discovery": args.etcd_cluster_init_discovery}
    if args.etcd_cluster_join_member_client is not None:
        config_sub["etcd"]["cluster"] = {"type": "join", "client": args.etcd_cluster_join_member_client}
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

    logger.info("Etcd config loaded.")

    # Load and modify config for main
    with open("config/templates/main.json", "r") as f:
        config_sub = json_comment.load(f)

    if args.retry_times is not None:
        config_sub["retry"]["times"] = args.retry_times
    if args.retry_interval is not None:
        config_sub["retry"]["interval"] = args.retry_interval
    if args.main_name is not None:
        if args.main_name == "ENV":
            config_sub["name"] = os.environ.get("NAME")
        else:
            config_sub["name"] = args.main_name
    if args.main_task_vacant is not None:
        config_sub["task"]["vacant"] = args.main_task_vacant
    if args.main_task_user_group is not None:
        user, group = args.main_task_user_group.split(':')
        config_sub["task"]["user"] = {"uid": pwd.getpwnam(user)[2], "gid": grp.getgrnam(group)[2]}
    if args.main_report_interval is not None:
        config_sub["report_interval"] = args.main_report_interval
    if args.main_print_log:
        config_sub.pop("log", None)
    if args.docker_sock is not None:
        config_sub["docker_sock"] = args.docker_sock
        config_sub["task"]["user"] = {"uid": pwd.getpwnam("executor")[2], "gid": grp.getgrnam("executor")[2]}
        if args.main_name is None:
            config_sub["name"] = socket.gethostname()
    with open("config/main.json", "w") as f:
        f.write(json.dumps(config_sub))
    services["main"] = {
        "pid_file": config_sub["pid_file"],
        "command": config_sub["exe"],
        "process": None
    }

    logger.info("Main config loaded.")

    # Generate pid files for service daemons
    for s in services:
        with open(services[s]["pid_file"], "w") as f:
            f.write("-1")

    # Generate start and exit order list
    start_order = ["etcd", "main"]
    exit_order = start_order[: : -1]

    # Check whether service daemons are running regularly
    check_services(start_order, exit_order, services, config["check_interval"], logger)

    logger.info("Executor boot program exiting.")
