# -*- encoding: utf-8 -*-

__author__ = "chenty"

import json
import configparser
import subprocess

from utility.function import get_logger, log_output, transform_address


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

def command_parser(parser):
    """
    Add uwsgi args to args parser
    :param parser: The args parser
    :return: Callback function to modify config
    """
    # Add needed args
    parser.add_argument("--uwsgi-host", dest="uwsgi_host", default=None,
                        help="Listen address of uwsgi")
    parser.add_argument("--uwsgi-port", dest="uwsgi_port", default=None,
                        help="Listen port of uwsgi")
    parser.add_argument("--uwsgi-process", type=int, dest="uwsgi_process", default=None,
                        help="Number of process of the uwsgi")
    parser.add_argument("--uwsgi-print-log", dest="uwsgi_print_log", action="store_const", const=True, default=False,
                        help="Print the log of uwsgi module to stdout")

    def conf_generator(args, config_sub, client, services, start_order):
        """
        Callback function to modify uwsgi configuration according to parsed args
        :param args: Parse args
        :param config_sub: Template config
        :param client: Docker client
        :param services: Dictionary of services
        :param start_order: List of services in starting order
        :return: None
        """
        # Modify config by parsed args
        if args.uwsgi_host is not None:
            config_sub["uwsgi"]["host"] = transform_address(args.uwsgi_host, client)
        if args.uwsgi_port is not None:
            config_sub["uwsgi"]["port"] = str(args.uwsgi_port)
        if args.uwsgi_process is not None:
            config_sub["uwsgi"]["process"] = args.uwsgi_process
        if args.uwsgi_print_log:
            config_sub["daemon"].pop("log_daemon", None)
            config_sub["daemon"].pop("log_uwsgi", None)
            config_sub["server"].pop("log_daemon", None)

        # Generate information for execution
        services["uwsgi"] = {
            "pid_file": config_sub["daemon"]["pid_file"],
            "command": config_sub["daemon"]["exe"],
            "process": None
        }
        start_order.append("uwsgi")
        return

    return conf_generator
