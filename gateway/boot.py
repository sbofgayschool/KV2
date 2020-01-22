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
import signal
import docker

from utility.function import get_logger, transform_address, check_services, sigterm_handler

# Register a signal for cleanup
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    # Parse all arguments
    parser = argparse.ArgumentParser(description="Gateway of Khala system. Provide HTTP API interface and a website.")
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
    parser.add_argument("--etcd-cluster-join-service", dest="etcd_cluster_join_service", default=None,
                        help="Service name if the etcd is going to use docker swarm and dns to auto detect members")
    parser.add_argument("--etcd-cluster-join-service-port", dest="etcd_cluster_join_service_port", default=None,
                        help="Etcd client port used for auto detection, default is 2001")
    parser.add_argument("--etcd-print-log", dest="etcd_print_log", action="store_const", const=True, default=False,
                        help="Print the log of etcd module to stdout")

    parser.add_argument("--uwsgi-host", dest="uwsgi_host", default=None,
                        help="Listen address of uwsgi")
    parser.add_argument("--uwsgi-port", dest="uwsgi_port", default=None,
                        help="Listen port of uwsgi")
    parser.add_argument("--uwsgi-process", type=int, dest="uwsgi_process", default=None,
                        help="Number of process of the uwsgi")
    parser.add_argument("--uwsgi-print-log", dest="uwsgi_print_log", action="store_const", const=True, default=False,
                        help="Print the log of uwsgi module to stdout")

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
    if args.etcd_cluster_join_service is not None:
        config_sub["etcd"]["cluster"] = {
            "type": "join",
            "service": args.etcd_cluster_join_service,
            "client_port":
                args.etcd_cluster_join_service_port if args.etcd_cluster_join_service_port is not None else "2001"
        }
    if args.etcd_print_log:
        config_sub["daemon"].pop("log_daemon", None)
        config_sub["daemon"].pop("log_etcd", None)
    if args.docker_sock is not None:
        config_sub["daemon"]["docker_sock"] = args.docker_sock
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

    # Load and modify config for uwsgi
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

    logger.info("Uwsgi config loaded.")

    # Generate pid files for service daemons
    for s in services:
        with open(services[s]["pid_file"], "w") as f:
            f.write("-1")

    # Generate start and exit order list
    start_order = ["etcd", "uwsgi"]
    exit_order = start_order[: : -1]

    # Check whether service daemons are running regularly
    check_services(start_order, exit_order, services, config["check_interval"], logger)

    logger.info("Gateway boot program exiting.")
