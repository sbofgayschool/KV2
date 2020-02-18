# -*- encoding: utf-8 -*-

__author__ = "chenty"

# Add current folder and parent folder into python path
import os
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.getcwd()))
import unittest
import multiprocessing
import signal
import time
import requests
import json
import flask
import shutil
import tracemalloc
tracemalloc.start()

from utility.boot.daemon import run
from utility.uwsgi.daemon import command_parser as uwsgi_parser


temp_server = flask.Flask(__name__)
@temp_server.route("/")
def index():
    return "Hello World!"

# Unit test class for utility.boot.daemon
class TestBootDaemon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Initialization function
        :return: None
        """
        print("Initializing environment.\n")

        # Generate configuration files
        with open("boot.json", "w") as f:
            f.write(json.dumps({"check_interval": 10}, indent=4))
        with open("uwsgi.json", "w") as f:
            f.write(json.dumps({
                "daemon": {
                    "exe": ["python3", "../gateway/uwsgi_daemon.py"],
                    "pid_file": "uwsgi.pid"
                },
                "uwsgi": {
                    "exe": ["uwsgi", "--ini", "uwsgi.ini"],
                    "host": "0.0.0.0",
                    "port": "7000",
                    "module": "test_boot_daemon:temp_server",
                    "master": True,
                    "process": 1
                }
            }, indent=4))
        os.mkdir("config")

        # Sub processes
        cls.boot = None
        return

    def test_000_run_boot_daemon(self):
        """
        Test to run boot daemon to start a uwsgi
        :return: None
        """
        cls = self.__class__

        # Generate all daemon
        service_list = [{
            "name": "main",
            "config_template": "uwsgi.json",
            "config": "config/uwsgi.json",
            "args_parser": uwsgi_parser
        }]
        cls.boot = multiprocessing.Process(target=run, args=(service_list, "Test", "Test only.", "boot.json"))
        cls.boot.daemon = True
        cls.boot.start()

        time.sleep(5)

        # Test http requests
        self.assertEqual(requests.get("http://localhost:7000/").text, "Hello World!")

        time.sleep(10)

        # Stop it
        os.kill(cls.boot.pid, signal.SIGINT)
        cls.boot.join()
        return

    @classmethod
    def tearDownClass(cls):
        """
        Cleaning function
        :return: None
        """
        print("Tearing down environment.\n")

        # Stop subprocess
        if cls.boot and cls.boot.is_alive():
            if cls.boot.pid:
                os.kill(cls.boot.pid, signal.SIGINT)
            cls.boot.join()

        # Remove config file
        os.remove("boot.json")
        os.remove("uwsgi.json")
        shutil.rmtree("config")
        os.remove("uwsgi.ini")
        os.remove("uwsgi.pid")
        return

if __name__ == "__main__":
    unittest.main()
