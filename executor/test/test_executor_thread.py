# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import os
import threading
import datetime
import zlib

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
        "id": None,
        "user": 1,
        "compile": {
            "source": b"",
            "command": zlib.compress(b"sleep 8\necho '???'"),
            "timeout": 10
        },
        "execute": {
            "input": zlib.compress(b"input\n"),
            "data": b"",
            "command": zlib.compress(b"while IFS= read -r line; do\n  printf '%s\n' \"$line\"\ndone\necho 'done~'"),
            "timeout": 3,
            "standard": b""
        },
        "add_time": None,
        "done": False,
        "status": 0,
        "executor": None,
        "report_time": datetime.datetime.now(),
        "result": None
    }
    executor.main.tasks = {"0": data}
    executor.main.tasks["0"]["id"] = "0"
    executor.main.tasks["0"]["process"] = None
    executor.main.tasks["0"]["cancel"] = False

    executor.main.tasks["0"]["thread"] = threading.Thread(target=executor.main.execute, args=("0", ))
    executor.main.tasks["0"]["thread"].setDaemon(True)
    executor.main.tasks["0"]["thread"].start()

    executor.main.tasks["0"]["thread"].join()

    print(executor.main.tasks["0"]["thread"].is_alive())
    print(executor.main.tasks)
