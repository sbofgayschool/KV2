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
import tracemalloc
tracemalloc.start()

from utility.uwsgi.daemon import run


temp_server = flask.Flask(__name__)
@temp_server.route("/")
def index():
    return "Hello World!"

# Unit test class for utility.uwsgi.daemon
class TestUwsgiDaemon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Initialization function
        :return: None
        """
        print("Initializing environment.\n")

        # Generate configuration files
        with open("conf.json", "w") as f:
            f.write(json.dumps({
                "daemon": {},
                "uwsgi": {
                    "exe": ["uwsgi", "--ini", "uwsgi.ini"],
                    "host": "0.0.0.0",
                    "port": "7000",
                    "module": "test_uwsgi_daemon:temp_server",
                    "master": True,
                    "process": 1
                }
            }, indent=4))

        # Sub processes
        cls.uwsgi = None
        return

    def test_000_run_uwsgi_daemon(self):
        """
        Test to run uwsgi through uwsgi daemon
        :return: None
        """
        cls = self.__class__

        # Generate all daemon
        cls.uwsgi = multiprocessing.Process(target=run, args=("Test", "conf.json"))
        cls.uwsgi.start()

        time.sleep(5)

        # Test http requests
        self.assertEqual(requests.get("http://localhost:7000/").text, "Hello World!")

        # Stop it
        os.kill(cls.uwsgi.pid, signal.SIGINT)
        cls.uwsgi.join()
        return

    @classmethod
    def tearDownClass(cls):
        """
        Cleaning function
        :return: None
        """
        print("Tearing down environment.\n")

        # Stop subprocess
        if cls.uwsgi and cls.uwsgi.is_alive():
            if cls.uwsgi.pid:
                os.kill(cls.uwsgi.pid, signal.SIGINT)
            cls.uwsgi.join()

        # Remove config file
        os.remove("conf.json")
        os.remove("uwsgi.ini")
        return

if __name__ == "__main__":
    unittest.main()
