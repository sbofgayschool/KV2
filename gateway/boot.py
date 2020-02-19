# -*- encoding: utf-8 -*-

__author__ = "chenty"

# Add current folder and parent folder into python path
import os
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.getcwd()))
import signal

from utility.etcd.daemon import command_parser as etcd_parser
from utility.uwsgi.daemon import command_parser as uwsgi_parser
from utility.boot.daemon import sigterm_handler, run


# Register a signal for cleanup
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    service_list = [{
        "name": "etcd",
        "config_template": "config/templates/etcd.json",
        "config": "config/etcd.json",
        "args_parser": etcd_parser,
        "args": (True, True)
    }, {
        "name": "uwsgi",
        "config_template": "config/templates/uwsgi.json",
        "config": "config/uwsgi.json",
        "args_parser": uwsgi_parser
    }]
    run(service_list, "Gateway", "Gateway of Khala system. Provide HTTP API interface and a website.")
