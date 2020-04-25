#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2020 SBofGaySchoolBuPaAnything
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

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
                    "processes": 2,
                    "threads": 2
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
        cls.uwsgi.daemon = True
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
