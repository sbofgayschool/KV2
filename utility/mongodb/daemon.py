# -*- encoding: utf-8 -*-

__author__ = "chenty"

import json
import subprocess
import threading
import time
import os
import shutil
import socket

from utility.function import get_logger, log_output, try_with_times, check_empty_dir, transform_address
from utility.etcd.proxy import generate_local_etcd_proxy
from utility.mongodb.proxy import mongodb_generate_run_command, generate_local_mongodb_proxy


# Symbol variable indicating whether the mongodb should be working
working = True

def register(config, local_etcd, local_mongodb, mongodb_proc, daemon_logger):
    """
    Target function for register thread
    Check the status of local mongodb, initialize its replica set configuration
    And then check if it has become the primary node, and update the corresponding key-value pair in etcd
    :param config: Config json of mongodb
    :param local_etcd: Local etcd proxy
    :param local_mongodb: Local mongodb proxy
    :param mongodb_proc: Subprocess object of mongodb
    :param daemon_logger: The logger
    :return: None
    """
    daemon_logger.info("Register thread started.")

    global working
    retry_times = config["daemon"]["retry"]["times"]
    retry_interval = config["daemon"]["retry"]["interval"]

    # Try to check whether the mongodb instance has started up by checking self status of local mongodb
    if not try_with_times(
        retry_times,
        retry_interval,
        True,
        daemon_logger,
        "check mongodb status",
        local_mongodb.check,
    )[0]:
        mongodb_proc.terminate()
        daemon_logger.error("Failed to start mongodb. Killing mongodb.")
        return

    advertise_address = config["mongodb"]["advertise"]["address"] + ":" + config["mongodb"]["advertise"]["port"]
    # If initialization should not be skipped, try to initialize the replica set (either initialize or join)
    if not try_with_times(
        retry_times,
        retry_interval,
        True,
        daemon_logger,
        "initialize or register local mongodb",
        local_mongodb.initialize,
        config["daemon"]["etcd_path"]["init"],
        config["daemon"]["etcd_path"]["register"]
    )[0]:
        mongodb_proc.terminate()
        daemon_logger.error("Failed to initialize nor register local mongodb. Killing mongodb.")
        return

    # Loop until termination to regularly check whether local mongodb has become primary node of the replica set
    daemon_logger.info("Starting mongodb register routine.")
    while working:
        time.sleep(config["daemon"]["register_interval"])
        try:
            registered_member = list(local_etcd.get(config["daemon"]["etcd_path"]["register"]).values())
            # If it is primary or this is the only registered node
            # Do the checkup
            if local_mongodb.is_primary() or (len(registered_member) == 1 and registered_member[0] == advertise_address):
                daemon_logger.info("Local mongodb is primary or the only registered node.")
                daemon_logger.info("Adjusting the replica set.")
                local_mongodb.adjust_replica_set(registered_member)
            else:
                daemon_logger.info("Local mongodb is secondary. There should be another node for regular adjustment.")
        except:
            daemon_logger.error("Failed to check primary status.", exc_info=True)

    daemon_logger.info("Register thread terminating.")
    return

def run(module_name="Judicator", etcd_conf_path="config/etcd.json", mongodb_conf_path="config/mongodb.json"):
    """
    Load config and run mongodb
    :param module_name: Name of the caller module
    :param etcd_conf_path: Path to etcd config file
    :param mongodb_conf_path: Path to mongodb config file
    :return: None
    """
    global working

    # Load configuration
    with open(mongodb_conf_path, "r") as f:
        config = json.load(f)
    retry_times = config["daemon"]["retry"]["times"]
    retry_interval = config["daemon"]["retry"]["interval"]

    # Generate logger for daemon
    if "log_daemon" in config["daemon"]:
        daemon_logger = get_logger(
            "mongodb_daemon",
            config["daemon"]["log_daemon"]["info"],
            config["daemon"]["log_daemon"]["error"]
        )
    else:
        daemon_logger = get_logger("mongodb_daemon", None, None)
    daemon_logger.info("%s mongodb_daemon program started." % module_name)

    # Generate logger for mongodb forwarding raw log output to designated place
    if "log_mongodb" in config["daemon"]:
        mongodb_logger = get_logger(
            "mongodb",
            config["daemon"]["log_mongodb"]["info"],
            config["daemon"]["log_mongodb"]["error"],
            True
        )
    else:
        mongodb_logger = get_logger("mongodb", None, None, True)

    # Get a etcd proxy for replica set operations
    with open(etcd_conf_path, "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], daemon_logger)
    # Get a local mongodb proxy
    local_mongodb = generate_local_mongodb_proxy(config["mongodb"], local_etcd, daemon_logger)

    # Check whether the data dir of mongodb is empty
    # If not, delete it and create a new one
    if not check_empty_dir(config["mongodb"]["data_dir"]):
        shutil.rmtree(config["mongodb"]["data_dir"])
        os.mkdir(config["mongodb"]["data_dir"])
        daemon_logger.info("Previous data directory deleted with a new one created.")

    # Check whether the init data dir of mongodb is empty
    # If not, copy it to the data dir
    if not check_empty_dir(config["mongodb"]["data_init_dir"]):
        shutil.rmtree(config["mongodb"]["data_dir"])
        shutil.copytree(config["mongodb"]["data_init_dir"], config["mongodb"]["data_dir"])
        daemon_logger.info("Found existing data initialize directory.")

    # Generate command and run mongodb instance as a subprocess
    command = mongodb_generate_run_command(config["mongodb"])
    for c in command:
        daemon_logger.info("Starting mongodb with command: " + c)
    mongodb_proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    # Create and start register thread
    register_thread = threading.Thread(
        target=register,
        args=(config, local_etcd, local_mongodb, mongodb_proc, daemon_logger)
    )
    register_thread.setDaemon(True)
    register_thread.start()

    # Log the output of mongodb instance until EOF or terminated
    try:
        log_output(mongodb_logger, mongodb_proc.stdout, config["daemon"]["raw_log_symbol_pos"])
        daemon_logger.info("Received EOF from mongodb.")
    except KeyboardInterrupt:
        daemon_logger.info("Received SIGINT. Cleaning up and exiting.", exc_info=True)
        # Stop the register thread
        working = False
        register_thread.join()
        # Kill the process
        if not local_mongodb.shutdown_and_close():
            daemon_logger.error("Killing the process.")
            mongodb_proc.terminate()
        mongodb_proc.wait()
        daemon_logger.info("Mongodb process exited.")
        # Register this mongodb as exited one
        try_with_times(
            retry_times,
            retry_interval,
            False,
            daemon_logger,
            "cancel registration of mongodb",
            local_mongodb.cancel_registration,
            config["daemon"]["etcd_path"]["register"]
        )
        daemon_logger.info("Removed local mongodb registration on etcd.")
    except:
        daemon_logger.error("Accidentally terminated. Killing mongodb process.", exc_info=True)
        mongodb_proc.terminate()
    # Wait until mongodb process exit
    mongodb_proc.wait()

    daemon_logger.info("%s mongodb_daemon program exiting." % module_name)
    return

def command_parser(parser):
    """
    Add mongodb args to args parser
    :param parser: The args parser
    :return: Callback function to modify config
    """
    # Add needed args
    parser.add_argument("--mongodb-exe", dest="mongodb_exe", default=None,
                        help="Path to mongodb executable file")
    parser.add_argument("--mongodb-name", dest="mongodb_name", default=None,
                        help="Name of the mongodb node")
    parser.add_argument("--mongodb-listen-address", dest="mongodb_listen_address", default=None,
                        help="Listen address of the mongodb node")
    parser.add_argument("--mongodb-listen-port", type=int, dest="mongodb_listen_port", default=None,
                        help="Listen port of the etcd node")
    parser.add_argument("--mongodb-advertise-address", dest="mongodb_advertise_address", default=None,
                        help="Advertise address of the mongodb node")
    parser.add_argument("--mongodb-advertise-port", dest="mongodb_advertise_port", default=None,
                        help="Advertise port of the etcd node")
    parser.add_argument("--mongodb-replica-set", dest="mongodb_replica_set", default=None,
                        help="Name of the replica set which the mongodb node is going to join")
    parser.add_argument("--mongodb-print-log", dest="mongodb_print_log", action="store_const", const=True,
                        default=False, help="Print the log of mongodb module to stdout")

    def conf_generator(args, config_sub, client, services, start_order):
        """
        Callback function to modify mongodb configuration according to parsed args
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

        # Generate information for execution
        services["mongodb"] = {
            "pid_file": config_sub["daemon"]["pid_file"],
            "command": config_sub["daemon"]["exe"],
            "process": None
        }
        start_order.append("mongodb")
        return

    return conf_generator
