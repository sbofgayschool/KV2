# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import subprocess
import threading
import time
import urllib.parse
import pymongo.errors
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
        local_mongodb.check_self_running,
    )[0]:
        mongodb_proc.kill()
        daemon_logger.error("Failed to start mongodb. Killing mongodb.")
        return

    advertise_address = config["mongodb"]["advertise"]["address"] + ":" + config["mongodb"]["advertise"]["port"]
    # If initialization should not be skipped, try to initialize the replica set (either initialize or join)
    if not config["daemon"].get("skip_init", False) and not try_with_times(
        retry_times,
        retry_interval,
        True,
        daemon_logger,
        "initialize or add local mongodb to replica set",
        local_mongodb.initialize_replica_set,
        advertise_address,
        urllib.parse.urljoin(config["daemon"]["etcd_path"]["register"], config["mongodb"]["name"]),
        config["daemon"]["etcd_path"]["register"],
        config["daemon"]["etcd_path"]["primary"],
        local_etcd
    )[0]:
        mongodb_proc.kill()
        daemon_logger.error("Failed to initialize nor add local mongodb to replica set. Killing mongodb.")
        return

    # When everything is done, switch the mode of mongodb proxy from single to replica
    if not try_with_times(
        retry_times,
        retry_interval,
        True,
        daemon_logger,
        "switch mode to replica",
        local_mongodb.reconnect,
        True
    )[0]:
        mongodb_proc.kill()
        daemon_logger.error("Failed to switch mongodb proxy from single to replica. Killing mongodb.")
        return

    # Loop until termination to regularly check whether local mongodb has become primary node of the replica set
    daemon_logger.info("Starting mongodb register routine.")
    while working:
        time.sleep(config["daemon"]["register_interval"])
        try:
            # If it is primary, update the key-value pair in etcd with its own advertise address
            if local_mongodb.get_primary() == advertise_address:
                local_etcd.set(
                    config["daemon"]["etcd_path"]["primary"],
                    advertise_address
                )
                daemon_logger.info("Local mongodb is primary. Updated etcd.")

                # Try to remove all exited mongodb from replica set
                daemon_logger.info("Removing exited nodes from replica set.")
                # Get all registered node first
                member_registered = local_etcd.get(config["daemon"]["etcd_path"]["register"]).values()
                member_in_rs = [
                    x["host"] for x in local_mongodb.client.admin.command("replSetGetConfig", 1)["config"]["members"]
                ]
                daemon_logger.info("Got registered member: %s." % str(member_registered))
                daemon_logger.info("Got member in replica set: %s." % str(member_in_rs))
                # Get all member in rs but not registered, remove them
                exiting = set([x for x in member_in_rs if x not in member_registered])
                daemon_logger.info("Got exiting member: %s." % str(exiting))
                for address in exiting:
                    # Remove from the replica set and then the list on etcd
                    try:
                        local_mongodb.remove_from_replica_set(address)
                        daemon_logger.info("Removed exited node %s from replica set." % address)
                    except:
                        daemon_logger.error("Failed to remove %s from replica set." % address, exc_info=True)
                daemon_logger.info("All exited nodes removed.")
            else:
                daemon_logger.info("Local mongodb is secondary.")
        except:
            daemon_logger.error("Failed to check and update primary status.", exc_info=True)

    daemon_logger.info("Register thread terminating.")
    return

def exit_from_replica_set():
    """
    Delete local mongodb from registered list
    :return: None
    """
    # Delete local mongodb from registered list
    local_etcd.delete(
        urllib.parse.urljoin(config["daemon"]["etcd_path"]["register"], config["mongodb"]["name"]),
        config["mongodb"]["advertise"]["address"] + ":" + config["mongodb"]["advertise"]["port"]
    )
    daemon_logger.info("Removed local mongodb registration on etcd.")
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
    local_mongodb = generate_local_mongodb_proxy(config["mongodb"], daemon_logger)

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
        try:
            pymongo.MongoClient("localhost", int(config["mongodb"]["listen"]["port"])).admin.command("shutdown", 1)
        except pymongo.errors.AutoReconnect:
            daemon_logger.info("Shutdown local mongodb.", exc_info=True)
        except Exception as e:
            daemon_logger.error("Failed to shutdown mongodb. Killing the process.", exc_info=True)
            mongodb_proc.kill()
        mongodb_proc.wait()
        daemon_logger.info("Mongodb process exited.")
        # Register this mongodb as exited one
        try_with_times(
            retry_times,
            retry_interval,
            False,
            daemon_logger,
            "mark local mongodb as exited",
            exit_from_replica_set
        )
    except:
        daemon_logger.error("Accidentally terminated. Killing mongodb process.", exc_info=True)
        mongodb_proc.kill()
    # Wait until mongodb process exit
    mongodb_proc.wait()
    daemon_logger.info("Judicator mongodb_daemon program exiting.")
