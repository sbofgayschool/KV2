# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import subprocess
import threading

from utility.function import get_logger, log_output, check_empty_dir, try_with_times
from utility.etcd import etcd_generate_run_command, generate_local_etcd_proxy, EtcdProxy


def check():
    """
    Target function of check thread
    Check the status of local etcd instance
    :return: Result code
    """
    daemon_logger.info("Check thread start to work.")
    # Check the status of local etcd with retry times and intervals
    if try_with_times(
        retry_times,
        retry_interval,
        daemon_logger,
        "check etcd status",
        local_etcd.get_self_status
    )[0]:
        return

    # If not success, kill the etcd subprocess.
    etcd_proc.kill()
    daemon_logger.error("Failed to start etcd. Killing etcd and exiting.")
    return

if __name__ == "__main__":
    # Load config file
    with open("config/etcd.json", "r") as f:
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
    # If not, etcd has been configured before, and the cluster initialization information should be skipped
    if not check_empty_dir(config["etcd"]["data_dir"]):
        del config["etcd"]["cluster"]
        daemon_logger.info("Found existing data directory. Skipping cluster parameters.")

    # If data dir is empty, this is a new etcd instance
    # It should be either initialized as joining an exist cluster, or initializing a new one
    if "cluster" in config["etcd"] and config["etcd"]["cluster"]["type"] == "join":
        # Generate a etcd proxy for the remote etcd to be joined
        remote_etcd = EtcdProxy(config["etcd"]["cluster"]["client"], daemon_logger)
        # Join the cluster by adding self information
        success, res = try_with_times(
            retry_times,
            retry_interval,
            daemon_logger,
            "add member to etcd cluster status",
            remote_etcd.add_and_get_members,
            "http://" + config["etcd"]["advertise"]["address"] + ":" + config["etcd"]["advertise"]["peer_port"]
        )
        if not success:
            daemon_logger.error("Failed to add member information to remote client. Exiting.")
            exit()
        # Generate member argument for the joining command
        config["etcd"]["cluster"]["member"] = ",".join([(k + "=" + v) for k, v in res.items()])

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
    check_thread = threading.Thread(target=check)
    check_thread.setDaemon(True)
    check_thread.start()

    # Log the raw output of etcd until it exist or this process encounter a signal
    try:
        log_output(etcd_logger, etcd_proc.stdout, 27)
        daemon_logger.info("Received EOF from etcd.")
    except:
        daemon_logger.error("Accidentally terminated. Killing etcd process.", exc_info=True)
        etcd_proc.kill()
    # Wait for the subprocess to prevent zombie process
    etcd_proc.wait()
    daemon_logger.info("Exiting.")
