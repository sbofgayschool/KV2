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

import json
import subprocess
import threading
import os
import shutil
import docker
import socket
import signal

from utility.function import get_logger, log_output, check_empty_dir, try_with_times, transform_address
from utility.etcd.proxy import etcd_generate_run_command, generate_local_etcd_proxy, EtcdProxy


def check(retry_times, retry_interval, etcd_proc, local_etcd, daemon_logger):
    """
    Target function of check thread
    Check the status of local etcd instance
    :param retry_times: Chances of retry
    :param retry_interval: Time interval between retry
    :param etcd_proc: Etcd process object
    :param local_etcd: Local Etcd proxy
    :param daemon_logger: The logger
    :return: Result code
    """
    daemon_logger.info("Check thread started.")
    # Check the status of local etcd with retry times and intervals
    if try_with_times(
        retry_times,
        retry_interval,
        True,
        daemon_logger,
        "check etcd status",
        local_etcd.get_self_status
    )[0]:
        daemon_logger.info("Etcd started.")
        return

    # If not success, kill the etcd subprocess.
    daemon_logger.error("Failed to start etcd. Killing etcd process.")
    etcd_proc.terminate()
    return

def run(module_name, etcd_conf_path="config/etcd.json"):
    """
    Load config and run etcd
    :param module_name: Name of the caller module
    :param etcd_conf_path: Path to etcd config file
    :return: None
    """
    # Load config file
    with open(etcd_conf_path, "r") as f:
        config = json.load(f)
    retry_times = config["daemon"]["retry"]["times"]
    retry_interval = config["daemon"]["retry"]["interval"]

    # Generate daemon logger from config file
    # If logger arguments exist in config file, write the log to the designated file
    # Else, forward the log to standard output
    if "log_daemon" in config["daemon"]:
        daemon_logger = get_logger(
            "etcd_daemon",
            config["daemon"]["log_daemon"]["info"],
            config["daemon"]["log_daemon"]["error"]
        )
    else:
        daemon_logger = get_logger("etcd_daemon", None, None)
    daemon_logger.info("%s etcd_daemon program started." % module_name)

    # Generate etcd logger forwarding etcd log to designated location
    if "log_etcd" in config["daemon"]:
        etcd_logger = get_logger(
            "etcd",
            config["daemon"]["log_etcd"]["info"],
            config["daemon"]["log_etcd"]["error"],
            True
        )
    else:
        etcd_logger = get_logger("etcd", None, None, True)

    # Generate a etcd proxy for local etcd
    local_etcd = generate_local_etcd_proxy(config["etcd"], daemon_logger)

    # Check whether the data dir of etcd is empty
    # If not, delete it and create a new one
    if not check_empty_dir(config["etcd"]["data_dir"]):
        shutil.rmtree(config["etcd"]["data_dir"])
        os.mkdir(config["etcd"]["data_dir"])
        daemon_logger.info("Previous data directory deleted with a new one created.")

    # Check whether the data dir of etcd is empty
    # If not, copy it to data dir, and the cluster initialization information should be skipped
    if "data_init_dir" in config["etcd"] and not check_empty_dir(config["etcd"]["data_init_dir"]):
        del config["etcd"]["cluster"]
        shutil.rmtree(config["etcd"]["data_dir"])
        shutil.copytree(config["etcd"]["data_init_dir"], config["etcd"]["data_dir"])
        daemon_logger.info("Found existing data initialize directory. Skipped cluster parameters.")

    # If cluster config exists, this node is going to either explicitly join a cluster or initialize one
    if "cluster" in config["etcd"]:
        # If service name of etcd member detection is specified, use it and find a member client
        if "service" in config["etcd"]["cluster"]:
            daemon_logger.info("Searching etcd member using docker service and dns.")
            # Get all running tasks of the specified service
            services = []
            try:
                client = docker.APIClient(base_url=config["daemon"]["docker_sock"])
                services = [
                    "http://" + config["etcd"]["cluster"]["service"] + "." + str(x["Slot"]) + "." + x["ID"] + ":" +
                    config["etcd"]["cluster"]["client_port"]
                    for x in sorted(
                        client.tasks({"service": config["etcd"]["cluster"]["service"]}), key=lambda x: x["CreatedAt"]
                    )
                    if x["Status"]["State"] == "running" and x["DesiredState"] == "running"
                ]
            except:
                daemon_logger.error("Failed to connect to docker engine.", exc_info=True)
                daemon_logger.error("%s etcd_daemon program exiting." % module_name)
                exit(1)
            # When local etcd is not in proxy mode, try to delete current task from service list, if it is found
            if "proxy" not in config["etcd"]:
                try:
                    services.remove(
                        "http://" + config["etcd"]["advertise"]["address"] +
                        ":" + config["etcd"]["advertise"]["client_port"]
                    )
                except:
                    daemon_logger.warning("Failed to find current docker task in list.", exc_info=True)
            else:
                daemon_logger.info("Detected proxy mode. Skipped removing current docker task from service list.")

            # If one or more docker service tasks are running, join the first created one
            # Else, initialize the cluster by itself if it is not in proxy mode, or exit
            if services:
                daemon_logger.info("Found following available members:")
                for x in services:
                    daemon_logger.info("%s" % x)
                config["etcd"]["cluster"] = {"type": "join", "client": services[0]}
                daemon_logger.info("Selected %s as member client." % config["etcd"]["cluster"]["client"])
            else:
                daemon_logger.warning("No available member detected.")
                if "proxy" not in config["etcd"]:
                    config["etcd"]["cluster"] = {"type": "init"}
                    daemon_logger.info("Initializing cluster by local etcd.")
                else:
                    daemon_logger.info("%s etcd_daemon program exiting." % module_name)
                    exit(1)

        # If the node is going join a cluster without knowing existing members
        # Add itself to the cluster if not in proxy mode
        # And then (in or not in proxy mode), get all member information for etcd start up command
        if config["etcd"]["cluster"]["type"] == "join" and not "member" in config["etcd"]["cluster"]:
            # Generate a etcd proxy for the remote etcd to be joined
            remote_etcd = EtcdProxy(config["etcd"]["cluster"]["client"], daemon_logger)
            # Join the cluster by adding self information
            success, res = try_with_times(
                retry_times,
                retry_interval,
                False,
                daemon_logger,
                "get (and add) member to etcd cluster status",
                remote_etcd.add_and_get_members,
                config["etcd"]["name"],
                "http://" + config["etcd"]["advertise"]["address"] + ":" + config["etcd"]["advertise"]["peer_port"],
                "proxy" in config["etcd"]
            )
            if not success:
                daemon_logger.error("Failed to get (and add) member information to remote client. Exiting.")
                exit(1)
            # Generate member argument for the joining command
            config["etcd"]["cluster"]["member"] = ",".join([(k + "=" + v) for k, v in res.items()])
            daemon_logger.info("Existing members of cluster received.")
            daemon_logger.info("Etcd will be started with member arguments: %s." % config["etcd"]["cluster"]["member"])

    # Generate running command
    command = etcd_generate_run_command(config["etcd"])
    for c in command:
        daemon_logger.info("Starting etcd with command: " + c)
    # Run etcd in a subprocess.
    etcd_proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    # Create a check thread to check if etcd has been started up
    check_thread = threading.Thread(
        target=check,
        args=(retry_times, retry_interval, etcd_proc, local_etcd, daemon_logger)
    )
    check_thread.setDaemon(True)
    check_thread.start()

    # Log the raw output of etcd until it exit or terminated
    try:
        log_output(etcd_logger, etcd_proc.stdout, config["daemon"]["raw_log_symbol_pos"])
        daemon_logger.info("Received EOF from etcd.")
    except KeyboardInterrupt:
        daemon_logger.info("Received SIGINT. Cleaning up and exiting.", exc_info=True)
        if "proxy" not in config["etcd"]:
            try_with_times(
                retry_times,
                retry_interval,
                False,
                daemon_logger,
                "remove etcd from cluster",
                local_etcd.remove_member,
                config["etcd"]["name"],
                "http://" + config["etcd"]["advertise"]["address"] + ":" + config["etcd"]["advertise"]["peer_port"]
            )
        else:
            daemon_logger.info("Detected proxy mode. Skipped removing local etcd from cluster.")
        os.kill(etcd_proc.pid, signal.SIGINT)
    except:
        daemon_logger.error("Accidentally terminated. Killing etcd process.", exc_info=True)
        etcd_proc.terminate()
    # Wait for the subprocess
    etcd_proc.wait()

    daemon_logger.info("%s etcd_daemon program exiting." % module_name)
    return

def command_parser(parser, fixed_address=False, join_only=False):
    """
    Add etcd args to args parser
    :param parser: The args parser
    :param fixed_address: If the etcd should use address provided by template config only
    :param join_only: If the etcd should only join a cluster
    :return: Callback function to modify config
    """
    # Add needed args
    parser.add_argument("--etcd-exe", dest="etcd_exe", default=None,
                        help="Path to etcd executable file")
    parser.add_argument("--etcd-name", dest="etcd_name", default=None,
                        help="Name of the etcd node")
    parser.add_argument("--etcd-proxy", dest="etcd_proxy", default=None,
                        help="If etcd node should be in proxy mode")
    parser.add_argument("--etcd-strict-reconfig", dest="etcd_strict_reconfig", action="store_const",
                        const=True, default=None, help="If the etcd should be in strict reconfig mode")
    if not fixed_address:
        parser.add_argument("--etcd-listen-address", dest="etcd_listen_address", default=None,
                            help="Listen address of the etcd node")
    parser.add_argument("--etcd-listen-peer-port", type=int, dest="etcd_listen_peer_port", default=None,
                        help="Listen peer port of the etcd node")
    parser.add_argument("--etcd-listen-client-port", type=int, dest="etcd_listen_client_port", default=None,
                        help="Listen client port of the etcd node")
    if not fixed_address:
        parser.add_argument("--etcd-advertise-address", dest="etcd_advertise_address", default=None,
                            help="Advertise address of the etcd node")
    parser.add_argument("--etcd-advertise-peer-port", dest="etcd_advertise_peer_port", default=None,
                        help="Advertise peer port of the etcd node")
    parser.add_argument("--etcd-advertise-client-port", dest="etcd_advertise_client_port", default=None,
                        help="Advertise client port of the etcd node")
    parser.add_argument("--etcd-cluster-init-discovery", dest="etcd_cluster_init_discovery", default=None,
                        help="Discovery token url of etcd node")
    if not join_only:
        parser.add_argument("--etcd-cluster-init-member", dest="etcd_cluster_init_member", default=None,
                            help="Name-url pairs used for initialized of etcd node")
        parser.add_argument("--etcd-cluster-init-independent", dest="etcd_cluster_init_independent",
                            action="store_const", const=True, default=None,
                            help="If the etcd node is going to be the only member of the cluster")
    parser.add_argument("--etcd-cluster-join-member-client", dest="etcd_cluster_join_member_client", default=None,
                        help="Client url of a member of the cluster which this etcd node is going to join")
    parser.add_argument("--etcd-cluster-service", dest="etcd_cluster_service", default=None,
                        help="Service name if the etcd is going to use docker swarm and dns to auto detect members")
    parser.add_argument("--etcd-cluster-service-port", type=int, dest="etcd_cluster_service_port", default=None,
                        help="Etcd client port used for auto detection, default is 2001")
    parser.add_argument("--etcd-print-log", dest="etcd_print_log", action="store_const", const=True, default=False,
                        help="Print the log of etcd module to stdout")

    def conf_generator(args, config_sub, client, services, start_order):
        """
        Callback function to modify etcd configuration according to parsed args
        :param args: Parse args
        :param config_sub: Template config
        :param client: Docker client
        :param services: Dictionary of services
        :param start_order: List of services in starting order
        :return: None
        """
        # Modify config by parsed args
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
        if (not fixed_address) and args.etcd_listen_address is not None:
            config_sub["etcd"]["listen"]["address"] = transform_address(args.etcd_listen_address, client)
        if args.etcd_listen_peer_port is not None:
            config_sub["etcd"]["listen"]["peer_port"] = str(args.etcd_listen_peer_port)
            config_sub["etcd"]["advertise"]["peer_port"] = str(args.etcd_listen_peer_port)
        if args.etcd_listen_client_port is not None:
            config_sub["etcd"]["listen"]["client_port"] = str(args.etcd_listen_client_port)
            config_sub["etcd"]["advertise"]["client_port"] = str(args.etcd_listen_client_port)
        if (not fixed_address) and args.etcd_advertise_address is not None:
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
        if (not join_only) and args.etcd_cluster_init_member is not None:
            config_sub["etcd"]["cluster"] = {"type": "init", "member": args.etcd_cluster_init_member}
        if (not join_only) and args.etcd_cluster_init_independent is not None:
            config_sub["etcd"]["cluster"] = {"type": "init"}
        if args.etcd_cluster_join_member_client is not None:
            config_sub["etcd"]["cluster"] = {"type": "join", "client": args.etcd_cluster_join_member_client}
        if args.etcd_cluster_service is not None:
            config_sub["etcd"]["cluster"] = {
                "service": args.etcd_cluster_service,
                "client_port":
                    str(args.etcd_cluster_service_port) if args.etcd_cluster_service_port is not None else "2001"
            }
        if args.etcd_print_log:
            config_sub["daemon"].pop("log_daemon", None)
            config_sub["daemon"].pop("log_etcd", None)
        if args.docker_sock is not None:
            config_sub["daemon"]["docker_sock"] = args.docker_sock
            config_sub["etcd"]["exe"] = "etcd"
            if args.etcd_name is None:
                config_sub["etcd"]["name"] = socket.gethostname()

        # Generate information for execution
        services["etcd"] = {
            "pid_file": config_sub["daemon"]["pid_file"],
            "command": config_sub["daemon"]["exe"],
            "process": None
        }
        start_order.append("etcd")
        return

    return conf_generator
