# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import os
import threading
import datetime

from utility.function import get_logger
import executor.main


if __name__ == "__main__":
    os.chdir("..")
    # Load configuration
    with open("config/templates/main.json", "r") as f:
        executor.main.config = json.load(f)
    retry_times = executor.main.config["retry"]["times"]
    retry_interval = executor.main.config["retry"]["interval"]

    # Generate a logger
    if "log" in executor.main.config:
        executor.main.logger = get_logger(
            "main",
            executor.main.config["log"]["info"],
            executor.main.config["log"]["error"]
        )
    else:
        executor.main.logger = get_logger("main", None, None)

    executor.main.lock = threading.Lock()

    data = {
        "id": "0",
        "user": 1,
        "compile": {
            "source": b"",
            # "command": b'x\x9c\xcb)V\xd0M\xcc\x01\x00\x07\x02\x01\xfa',
            # "command": b'x\x9c+\xceIM-P0\xe5JM\xce\xc8WP\xb7\xb7\xb7W\x07\x007\xd0\x05C',
            "command": b'x\x9c+\xceIM-P0\xe2JM\xce\xc8WP\xb7\xb7\xb7W\x07\x007\xac\x05@',
            "timeout": 3
        },
        "execute": {
            "input": b'x\x9c\x03\x00\x00\x00\x00\x01',
            "data": b"",
            "command": b'x\x9cKM\xce\xc8WPO,NIS\x07\x00\x16\xfa\x03\xac',
            "timeout": 3,
            "standard": b""
        },
        "done": False,
        "status": 0,
        "executor": None,
        "report_time": datetime.datetime.now(),
        "result": None
    }
    executor.main.tasks = {"0": data}
    executor.main.tasks["0"]["process"] = None
    executor.main.tasks["0"]["cancel"] = False

    executor.main.tasks["0"]["thread"] = threading.Thread(target=executor.main.execute, args=("0", ))
    executor.main.tasks["0"]["thread"].setDaemon(True)
    executor.main.tasks["0"]["thread"].start()

    executor.main.tasks["0"]["thread"].join()

    print(executor.main.tasks["0"]["thread"].is_alive())
    print(executor.main.tasks)
