# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import subprocess
import threading
import time

from utility.function import get_logger, log_output, try_with_times
from utility.etcd import generate_local_etcd_proxy
from utility.mongodb import mongodb_generate_run_command, generate_local_mongodb_proxy


def register():
    """
    Target function for register thread
    Check the status of local mongodb, initialize its replica set configuration
    And then check if it has become the primary node, and update the corresponding key-value pair in etcd
    :return: Result Code
    """
    daemon_logger.info("Register thread start to work.")
    # Try to check whether the mongodb instance has started up by checking self status of local mongodb
    if not try_with_times(
        retry_times,
        retry_interval,
        daemon_logger,
        "check mongodb status",
        local_mongodb.check_self_running,
    )[0]:
        mongodb_proc.kill()
        daemon_logger.error("Failed to start mongodb. Killing mongodb and exiting.")
        return

    # Try to initialize the replica set (either initialize or join)
    if not try_with_times(
        retry_times,
        retry_interval,
        daemon_logger,
        "initialize or add local mongodb to replica set",
        local_mongodb.initialize_replica_set,
        config["mongodb"]["advertise"]["address"] + ":" + config["mongodb"]["advertise"]["port"],
        local_etcd,
        config["daemon"]["etcd_path"]["primary"]
    )[0]:
        mongodb_proc.kill()
        daemon_logger.error("Failed to initialize nor add local mongodb to replica set. Killing mongodb and exiting.")
        return

    # Loop forever to regularly check whether local mongodb has become primary node of the replica set
    while True:
        time.sleep(config["daemon"]["register_interval"])
        try:
            # If it is primary, update the key-value pair in etcd with its own advertise address
            if local_mongodb.check_primary():
                local_etcd.set(
                    config["daemon"]["etcd_path"]["primary"],
                    config["mongodb"]["advertise"]["address"] + ":" + config["mongodb"]["advertise"]["port"]
                )
                daemon_logger.info("Local mongodb is primary. Updated etcd.")
            else:
                daemon_logger.info("Local mongodb is secondary.")
        except:
            daemon_logger.error("Failed to check and update primary status.", exc_info=True)

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
    local_mongodb = generate_local_mongodb_proxy(config["mongodb"], daemon_logger)

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
    register_thread = threading.Thread(target=register)
    register_thread.setDaemon(True)
    register_thread.start()

    # Log the output of mongodb instance until EOF or a signal is received
    try:
        log_output(mongodb_logger, mongodb_proc.stdout, 29)
        daemon_logger.info("Received EOF from mongodb.")
    except:
        # When a signal is received, kill the subprocess
        daemon_logger.error("Received signal, killing mongodb process.", exc_info=True)
        mongodb_proc.kill()
    # Wait until mongodb process exit
    mongodb_proc.wait()
    daemon_logger.info("Exiting.")
