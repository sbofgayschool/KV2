# -*- encoding: utf-8 -*-

__author__ = "chenty"

import subprocess
import threading
from jsoncomment import JsonComment

from utility.function import get_logger, check_empty_dir, try_with_times
from utility.etcd import etcd_log_output, etcd_generate_run_command, etcd_get_self_status, etcd_add_and_get_members
from utility.define import RETURN_CODE

json = JsonComment()


def check():
    if try_with_times(
        retry_times,
        retry_interval,
        daemon_logger,
        "check etcd status",
        etcd_get_self_status,
        "http://127.0.0.1:" + config["etcd"]["listen"]["client_port"]
    )[0]:
        return RETURN_CODE["OK"]
    etcd_proc.kill()
    daemon_logger.error("Failed to start etcd. Killing etcd and exiting.")
    return RETURN_CODE["ERROR"]

if __name__ == "__main__":
    with open("config/etcd.json", "r") as f:
        config = json.load(f)
    retry_times = config["daemon"]["retry"]["times"]
    retry_interval = config["daemon"]["retry"]["interval"]

    if "log_daemon" in config["daemon"]:
        daemon_logger = get_logger(
            "daemon",
            config["daemon"]["log_daemon"]["info"],
            config["daemon"]["log_daemon"]["error"]
        )
    else:
        daemon_logger = get_logger("daemon", None, None)

    if "log_etcd" in config["daemon"]:
        etcd_logger = get_logger(
            "etcd",
            config["daemon"]["log_etcd"]["info"],
            config["daemon"]["log_etcd"]["error"],
            True
        )
    else:
        etcd_logger = get_logger("etcd", None, None, True)

    if not check_empty_dir(config["etcd"]["data_dir"]):
        del config["etcd"]["cluster"]
        daemon_logger.info("Found existing data directory. Skipping cluster parameters.")

    if "cluster" in config["etcd"] and config["etcd"]["cluster"]["type"] == "join":
        success, res = try_with_times(
            retry_times,
            retry_interval,
            daemon_logger,
            "add member to etcd cluster status",
            etcd_add_and_get_members,
            config["etcd"]["cluster"]["client"],
            "http://" + config["etcd"]["advertise"]["address"] + ":" + config["etcd"]["advertise"]["peer_port"]
        )
        if not success:
            daemon_logger.error("Failed to add member information to remote client. Exiting.")
            exit(RETURN_CODE["ERROR"])
        config["etcd"]["cluster"]["member"] = ",".join([(k + "=" + v) for k, v in res.items()])

    command = etcd_generate_run_command(config["etcd"])
    for c in command:
        daemon_logger.info("Starting etcd with command: " + c)
    etcd_proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    check_thread = threading.Thread(target=check)
    check_thread.setDaemon(True)
    check_thread.start()

    try:
        etcd_log_output(etcd_logger, etcd_proc.stdout)
        daemon_logger.info("Received EOF from etcd.")
    except:
        daemon_logger.error("Received signal, killing etcd process.", exc_info=True)
        etcd_proc.kill()
        etcd_proc.wait()
    daemon_logger.info("Exiting.")
