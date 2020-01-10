# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import configparser
import subprocess

from utility.function import get_logger, log_output


if __name__ == "__main__":
    # Load config file
    with open("config/uwsgi.json", "r") as f:
        config = json.load(f)

    # Generate ini config file for uwsgi
    ini = configparser.ConfigParser()
    ini["uwsgi"] = {
        "http": config["uwsgi"]["host"] + ":" + config["uwsgi"]["port"],
        "module": config["uwsgi"]["module"],
        "process": config["uwsgi"]["process"],
        "master": config["uwsgi"]["master"]
    }
    with open(config["uwsgi"]["exe"][-1], "w") as f:
        ini.write(f)

    # Generate daemon logger from config file
    # If logger arguments exist in config file, write the log to the designated file
    # Else, forward the log to standard output
    if "log_daemon" in config["daemon"]:
        daemon_logger = get_logger(
            "uwsgi_daemon",
            config["daemon"]["log_daemon"]["info"],
            config["daemon"]["log_daemon"]["error"]
        )
    else:
        daemon_logger = get_logger("uwsgi_daemon", None, None)
    daemon_logger.info("Gateway uwsgi daemon program started.")

    # Generate uwsgi logger forwarding uwsgi log to designated location
    if "log_uwsgi" in config["daemon"]:
        uwsgi_logger = get_logger(
            "uwsgi",
            config["daemon"]["log_uwsgi"]["info"],
            config["daemon"]["log_uwsgi"]["error"],
            True
        )
    else:
        uwsgi_logger = get_logger("uwsgi", None, None, True)

    command = config["uwsgi"]["exe"]
    for c in command:
        daemon_logger.info("Starting uwsgi with command: " + c)
    # Run uwsgi in a subprocess.
    uwsgi_proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    # Log the raw output of uwsgi until it exit or terminated
    try:
        log_output(uwsgi_logger, uwsgi_proc.stdout, None)
        daemon_logger.info("Received EOF from uwsgi.")
    except KeyboardInterrupt:
        daemon_logger.info("SIGINT Received. Killing uwsgi process.", exc_info=True)
        uwsgi_proc.kill()
    except:
        daemon_logger.error("Accidentally terminated. Killing uwsgi process.", exc_info=True)
        uwsgi_proc.kill()
    # Wait for the subprocess to prevent zombie process
    uwsgi_proc.wait()
    daemon_logger.info("Exiting.")
