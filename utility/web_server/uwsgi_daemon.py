# -*- encoding: utf-8 -*-

__author__ = "chenty"

import json
import configparser
import subprocess

from utility.function import get_logger, log_output


def run(module_name="Gateway", uwsgi_conf_path="config/uwsgi.json"):
    """
    Load config and run uwsgi
    :param module_name: Name of the caller module
    :param uwsgi_conf_path: Path to uwsgi config file
    :return: None
    """
    # Load config file
    with open(uwsgi_conf_path, "r") as f:
        config = json.load(f)

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
    daemon_logger.info("%s uwsgi_daemon program started." % module_name)

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
    daemon_logger.info("Generated ini file for uwsgi.")

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
        daemon_logger.info("Received SIGINT. Killing uwsgi process.", exc_info=True)
        uwsgi_proc.kill()
    except:
        daemon_logger.error("Accidentally terminated. Killing uwsgi process.", exc_info=True)
        uwsgi_proc.kill()
    # Wait for the subprocess to prevent zombie process
    uwsgi_proc.wait()

    daemon_logger.info("%s uwsgi_daemon program exiting." % module_name)
    return
