# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import subprocess
import threading
import time
import urllib.parse
import os
import shutil

from utility.function import get_logger, log_output, try_with_times, check_empty_dir
from utility.etcd import generate_local_etcd_proxy
from utility.mongodb import mongodb_generate_run_command, generate_local_mongodb_proxy


def register():
    """
    Target function for register thread
    Check the status of local mongodb, initialize its replica set configuration
    And then check if it has become the primary node, and update the corresponding key-value pair in etcd
    :return: Result Code
    """
    daemon_logger.info("Register thread started.")
    # Try to check whether the mongodb instance has started up by checking self status of local mongodb
    if not try_with_times(
        retry_times,
        retry_interval,
        True,
        daemon_logger,
        "check mongodb status",
        local_mongodb.check,
    )[0]:
        mongodb_proc.kill()
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
        mongodb_proc.kill()
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

if __name__ == "__main__":
    # Load configuration
    with open("config/mongodb.json", "r") as f:
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
    daemon_logger.info("Judicator mongodb_daemon program started.")

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
    with open("config/etcd.json", "r") as f:
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
        shutil.copytree(config["mongodb"]["init_data_dir"], config["mongodb"]["data_dir"])
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
    working = True
    register_thread = threading.Thread(target=register)
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
            mongodb_proc.kill()
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
        mongodb_proc.kill()
    # Wait until mongodb process exit
    mongodb_proc.wait()
    daemon_logger.info("Judicator mongodb_daemon program exiting.")
