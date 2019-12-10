# -*- encoding: utf-8 -*-

__author__ = "chenty"

import subprocess
import threading
from jsoncomment import JsonComment
import pymongo

from utility.function import get_logger, log_output, try_with_times
from utility.etcd import generate_local_etcd_proxy
from utility.mongodb import mongodb_generate_run_command, generate_local_mongodb_proxy, MongoDBProxy
from utility.define import RETURN_CODE

json = JsonComment()


def register():
    if not try_with_times(
        retry_times,
        retry_interval,
        daemon_logger,
        "check mongodb status",
        local_mongodb.check_self_running,
    )[0]:
        mongodb_proc.kill()
        daemon_logger.error("Failed to start mongodb. Killing mongodb and exiting.")
        return RETURN_CODE["ERROR"]

    if not try_with_times(
        retry_times,
        retry_interval,
        daemon_logger,
        "initialize or add this to mongodb replica set",
        local_mongodb.initialize_replica_set,
        config["mongodb"]["advertise"]["address"] + ":" + config["mongodb"]["advertise"]["port"],
        local_etcd,
        config["daemon"]["etcd_path"]["primary"]
    )[0]:
        mongodb_proc.kill()
        daemon_logger.error("Failed to initialize nor add this to mongodb replica set. Killing mongodb and exiting.")
        return RETURN_CODE["ERROR"]

    while True:
        IF this.mongodb.primary_member == this.mongodb:
            this.etcd.mongodb / primary.set(this.mongodb)
        sleep(duration)

if __name__ == "__main__":
    with open("config/etcd.json", "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"])
    with open("config/mongodb.json", "r") as f:
        config = json.load(f)
        local_mongodb = generate_local_mongodb_proxy(config["mongodb"])
    retry_times = config["daemon"]["retry"]["times"]
    retry_interval = config["daemon"]["retry"]["interval"]

    if "log_daemon" in config["daemon"]:
        daemon_logger = get_logger(
            "mongodb_daemon",
            config["daemon"]["log_daemon"]["info"],
            config["daemon"]["log_daemon"]["error"]
        )
    else:
        daemon_logger = get_logger("mongodb_daemon", None, None)

    if "log_mongodb" in config["daemon"]:
        mongodb_logger = get_logger(
            "mongodb",
            config["daemon"]["log_mongodb"]["info"],
            config["daemon"]["log_mongodb"]["error"],
            True
        )
    else:
        mongodb_logger = get_logger("mongodb", None, None, True)

    command = mongodb_generate_run_command(config["mongodb"])
    for c in command:
        daemon_logger.info("Starting mongodb with command: " + c)
    mongodb_proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    with open(config["daemon"]["pid_file"], "w") as f:
        f.write(str(mongodb_proc.pid))
        f.flush()

    register_thread = threading.Thread(target=register)
    register_thread.setDaemon(True)
    register_thread.start()

    try:
        log_output(mongodb_logger, mongodb_proc.stdout, 29)
        daemon_logger.info("Received EOF from mongodb.")
    except:
        daemon_logger.error("Received signal, killing mongodb process.", exc_info=True)
        mongodb_proc.kill()
        mongodb_proc.wait()
    daemon_logger.info("Exiting.")
