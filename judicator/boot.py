# -*- encoding: utf-8 -*-

__author__ = "chenty"

# Add current folder and parent folder into python path
import os
os.environ["PYTHONPATH"] += ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())
import signal

from utility.etcd.daemon import command_parser as etcd_parser
from utility.mongodb.daemon import command_parser as mongodb_parser
from judicator.main import command_parser as main_parser
from utility.boot.daemon import sigterm_handler, run


# Register a signal for cleanup
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    service_list = [{
        "name": "etcd",
        "config_template": "config/templates/etcd.json",
        "config": "config/etcd.json",
        "generator": etcd_parser
    }, {
        "name": "mongodb",
        "config_template": "config/templates/mongodb.json",
        "config": "config/mongodb.json",
        "generator": mongodb_parser
    }, {
        "name": "main",
        "config_template": "config/templates/main.json",
        "config": "config/main.json",
        "generator": main_parser
    }]
    run(service_list, "Judicator", "Judicator of Khala system. Handle requests and maintain task data.")
