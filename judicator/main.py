# -*- encoding: utf-8 -*-

__author__ = "chenty"

import subprocess
import threading
import time
import urllib.parse
from jsoncomment import JsonComment

from utility.function import get_logger, try_with_times
from utility.etcd import generate_local_etcd_proxy
from utility.mongodb import generate_local_mongodb_proxy
from utility.define import RETURN_CODE

json = JsonComment()


def register():
    reg_key = urllib.parse.urljoin(config["register"]["etcd_path"], config["name"])
    reg_value = config["advertise"]["address"] + ":" + config["advertise"]["port"]
    while True:
        time.sleep(config["register"]["interval"])
        try:
            local_etcd.set()

if __name__ == "__main__":
    with open("config/main.json", "r") as f:
        config = json.load(f)
    retry_times = config["retry"]["times"]
    retry_interval = config["retry"]["interval"]

    if "log" in config:
        logger = get_logger(
            "main",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("main", None, None)

    with open("config/etcd.json", "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)
    with open("config/mongodb.json", "r") as f:
        local_mongodb = generate_local_mongodb_proxy(json.load(f)["mongodb"], logger)