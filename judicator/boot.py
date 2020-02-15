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
import docker
import signal

from utility.function import get_logger, transform_address, check_services, sigterm_handler


# Register a signal for cleanup
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    # Parse all arguments
    parser = argparse.ArgumentParser(description="Judicator of Khala system. Handle requests and maintain task data.")
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
    parser.add_argument("--etcd-proxy", dest="etcd_proxy", default=None,
                        help="If etcd node should be in proxy mode")
    parser.add_argument("--etcd-strict-reconfig", dest="etcd_strict_reconfig", action="store_const",
                        const=True, default=None, help="If the etcd should be in strict reconfig mode")
    parser.add_argument("--etcd-listen-address", dest="etcd_listen_address", default=None,
                        help="Listen address of the etcd node, default is 0.0.0.0")
    parser.add_argument("--etcd-listen-peer-port", type=int, dest="etcd_listen_peer_port", default=None,
                        help="Listen peer port of the etcd node, default is 2000")
    parser.add_argument("--etcd-listen-client-port", type=int, dest="etcd_listen_client_port", default=None,
                        help="Listen client port of the etcd node, default is 2001")
    parser.add_argument("--etcd-advertise-address", dest="etcd_advertise_address", default=None,
                        help="Advertise address of the etcd node, default is localhost")
    parser.add_argument("--etcd-advertise-peer-port",  dest="etcd_advertise_peer_port", default=None,
                        help="Advertise address of the etcd node, default is 2000")
    parser.add_argument("--etcd-advertise-client-port", dest="etcd_advertise_client_port", default=None,
                        help="Advertise peer port of the etcd node, default is 2001")
    parser.add_argument("--etcd-cluster-init-discovery", dest="etcd_cluster_init_discovery", default=None,
                        help="Discovery token url of etcd node")
    parser.add_argument("--etcd-cluster-init-member", dest="etcd_cluster_init_member", default=None,
                        help="Name-url pairs used for initialized of etcd node")
    parser.add_argument("--etcd-cluster-init-independent", dest="etcd_cluster_init_independent", action="store_const",
                        const=True, default=None, help="If the etcd node is going to be the only member of the cluster")
    parser.add_argument("--etcd-cluster-join-member-client", dest="etcd_cluster_join_member_client", default=None,
                        help="Client url of a member of the cluster which this etcd node is going to join")
    parser.add_argument("--etcd-cluster-join-service", dest="etcd_cluster_join_service", default=None,
                        help="Service name if the etcd is going to use docker swarm and dns to auto detect members")
    parser.add_argument("--etcd-cluster-join-service-port", dest="etcd_cluster_join_service_port", default=None,
                        help="Etcd client port used for auto detection, default is 2001")
    parser.add_argument("--etcd-print-log", dest="etcd_print_log", action="store_const", const=True, default=False,
                        help="Print the log of etcd module to stdout")

    parser.add_argument("--mongodb-exe", dest="mongodb_exe", default=None,
                        help="Path to mongodb executable file")
    parser.add_argument("--mongodb-name", dest="mongodb_name", default=None,
                        help="Name of the mongodb node")
    parser.add_argument("--mongodb-listen-address", dest="mongodb_listen_address", default=None,
                        help="Listen address of the mongodb node, default is 0.0.0.0")
    parser.add_argument("--mongodb-listen-port", type=int, dest="mongodb_listen_port", default=None,
                        help="Listen port of the etcd node, default is 3000")
    parser.add_argument("--mongodb-advertise-address", dest="mongodb_advertise_address", default=None,
                        help="Advertise address of the mongodb node, default is localhost")
    parser.add_argument("--mongodb-advertise-port", dest="mongodb_advertise_port", default=None,
                        help="Advertise port of the etcd node, default is 3000")
    parser.add_argument("--mongodb-replica-set", dest="mongodb_replica_set", default=None,
                        help="Name of the replica set which the mongodb node is going to join")
    parser.add_argument("--mongodb-print-log", dest="mongodb_print_log", action="store_const", const=True,
                        default=False, help="Print the log of mongodb module to stdout")

    parser.add_argument("--main-name", dest="main_name", default=None)
    parser.add_argument("--main-listen-address", dest="main_listen_address", default=None,
                        help="Listen address of judicator rpc service")
    parser.add_argument("--main-listen-port", type=int, dest="main_listen_port", default=None,
                        help="Listen port of judicator rpc service")
    parser.add_argument("--main-advertise-address", dest="main_advertise_address", default=None,
                        help="Advertise address of judicator rpc service")
    parser.add_argument("--main-advertise-port", dest="main_advertise_port", default=None,
                        help="Advertise port of judicator rpc service")
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
        logger = get_logger("boot", config["log"]["info"], config["log"]["error"])
    else:
        logger = get_logger("boot", None, None)
    logger.info("Judicator boot program started.")

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
    if args.etcd_proxy is not None:
        config_sub["etcd"]["proxy"] = args.etcd_proxy
    if args.etcd_strict_reconfig is not None:
        config_sub["etcd"]["strict_reconfig"] = args.etcd_strict_reconfig
    if args.etcd_listen_address is not None:
        config_sub["etcd"]["listen"]["address"] = transform_address(args.etcd_listen_address, client)
    if args.etcd_listen_peer_port is not None:
        config_sub["etcd"]["listen"]["peer_port"] = str(args.etcd_listen_peer_port)
        config_sub["etcd"]["advertise"]["peer_port"] = str(args.etcd_listen_peer_port)
    if args.etcd_listen_client_port is not None:
        config_sub["etcd"]["listen"]["client_port"] = str(args.etcd_listen_client_port)
        config_sub["etcd"]["advertise"]["client_port"] = str(args.etcd_listen_client_port)
    if args.etcd_advertise_address is not None:
        config_sub["etcd"]["advertise"]["address"] = transform_address(args.etcd_advertise_address, client)
    if args.etcd_advertise_peer_port is not None:
        if args.etcd_advertise_peer_port == "DOCKER":
            config_sub["etcd"]["advertise"]["peer_port"] = str(
                client.port(socket.gethostname(), int(config_sub["etcd"]["listen"]["peer_port"]))[0]["HostPort"]
            )
        else:
            config_sub["etcd"]["advertise"]["peer_port"] = str(args.etcd_advertise_peer_port)
    if args.etcd_advertise_client_port is not None:
        if args.etcd_advertise_client_port == "DOCKER":
            config_sub["etcd"]["advertise"]["client_port"] = str(
                client.port(socket.gethostname(), int(config_sub["etcd"]["listen"]["client_port"]))[0]["HostPort"]
            )
        else:
            config_sub["etcd"]["advertise"]["client_port"] = str(args.etcd_advertise_client_port)
    if args.etcd_cluster_init_discovery is not None:
        config_sub["etcd"]["cluster"] = {"type": "init", "discovery": args.etcd_cluster_init_discovery}
    if args.etcd_cluster_init_member is not None:
        config_sub["etcd"]["cluster"] = {"type": "init", "member": args.etcd_cluster_init_member}
    if args.etcd_cluster_init_independent is not None:
        config_sub["etcd"]["cluster"] = {"type": "init"}
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

    # Load and modify config for mongodb
    with open("config/templates/mongodb.json", "r") as f:
        config_sub = json_comment.load(f)

    if args.retry_times is not None:
        config_sub["daemon"]["retry"]["times"] = args.retry_times
    if args.retry_interval is not None:
        config_sub["daemon"]["retry"]["interval"] = args.retry_interval
    if args.mongodb_exe is not None:
        config_sub["mongodb"]["exe"] = args.mongodb_exe
    if args.mongodb_name is not None:
        if args.mongodb_name == "ENV":
            config_sub["mongodb"]["name"] = os.environ.get("NAME")
        else:
            config_sub["mongodb"]["name"] = args.mongodb_name
    if args.mongodb_listen_address is not None:
        config_sub["mongodb"]["listen"]["address"] = transform_address(args.mongodb_listen_address, client)
    if args.mongodb_listen_port is not None:
        config_sub["mongodb"]["listen"]["port"] = str(args.mongodb_listen_port)
        config_sub["mongodb"]["advertise"]["port"] = str(args.mongodb_listen_port)
    if args.mongodb_advertise_address is not None:
        config_sub["mongodb"]["advertise"]["address"] = transform_address(args.mongodb_advertise_address, client)
    if args.mongodb_advertise_port is not None:
        if args.mongodb_advertise_port == "DOCKER":
            config_sub["mongodb"]["advertise"]["port"] = str(
                client.port(socket.gethostname(), int(config_sub["mongodb"]["listen"]["port"]))[0]["HostPort"]
            )
        else:
            config_sub["mongodb"]["advertise"]["port"] = str(args.mongodb_advertise_port)
    if args.mongodb_replica_set is not None:
        config_sub["mongodb"]["replica_set"] = args.mongodb_replica_set
    if args.mongodb_print_log:
        config_sub["daemon"].pop("log_daemon", None)
        config_sub["daemon"].pop("log_mongodb", None)
    if args.docker_sock is not None:
        config_sub["mongodb"]["exe"] = "mongod"
        if args.mongodb_name is None:
            config_sub["mongodb"]["name"] = socket.gethostname()

    with open("config/mongodb.json", "w") as f:
        f.write(json.dumps(config_sub))
    services["mongodb"] = {
        "pid_file": config_sub["daemon"]["pid_file"],
        "command": config_sub["daemon"]["exe"],
        "process": None
    }

    logger.info("Mongodb config loaded.")

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
    if args.main_listen_address is not None:
        config_sub["listen"]["address"] = transform_address(args.main_listen_address, client)
    if args.main_listen_port is not None:
        config_sub["listen"]["port"] = str(args.main_listen_port)
        config_sub["advertise"]["port"] = str(args.main_listen_port)
    if args.main_advertise_address is not None:
        config_sub["advertise"]["address"] = transform_address(args.main_advertise_address, client)
    if args.main_advertise_port is not None:
        if args.main_advertise_port == "DOCKER":
            config_sub["advertise"]["port"] = str(
                client.port(socket.gethostname(), int(config_sub["listen"]["port"]))[0]["HostPort"]
            )
        else:
            config_sub["advertise"]["port"] = str(args.main_advertise_port)
    if args.main_print_log:
        config_sub.pop("log", None)
    if args.docker_sock is not None:
        if args.main_name is None:
            config_sub["name"] = socket.gethostname()
        client = docker.APIClient(base_url=args.docker_sock)

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
    start_order = ["etcd", "mongodb", "main"]
    exit_order = start_order[: : -1]

    # Check whether service daemons are running regularly
    check_services(start_order, exit_order, services, config["check_interval"], logger)

    logger.info("Judicator boot program exiting.")
