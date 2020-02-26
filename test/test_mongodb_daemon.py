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
import shutil
import tracemalloc
import json
import pymongo
tracemalloc.start()

from utility.mongodb.daemon import run
from utility.etcd.daemon import run as etcd_run
from utility.etcd.proxy import EtcdProxy
from utility.function import get_logger


# Unit test class for utility.mongodb.daemon
class TestMongodbDaemon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Initialization function
        :return: None
        """
        print("Initializing environment.\n")
        # Generate temp dirs
        for d in ["mongodb1", "mongodb2", "mongodb3"]:
            os.mkdir(d)
            for sd in ["mongodb", "mongodb_init"]:
                os.mkdir(d + "/" + sd)
        for d in ["etcd"]:
            os.mkdir(d)
            for sd in ["etcd", "etcd_init"]:
                os.mkdir(d + "/" + sd)

        # Generate configuration files
        with open("etcd/conf.json", "w") as f:
            f.write(json.dumps({
                "daemon": {
                    "retry": {
                        "times": 3,
                        "interval": 5
                    },
                    "raw_log_symbol_pos": 27,
                },
                "etcd": {
                    "exe": "etcd",
                    "name": "etcd",
                    "data_dir": "etcd/etcd",
                    "data_init_dir": "etcd/etcd_init",
                    "listen": {
                        "address": "0.0.0.0",
                        "peer_port": "2000",
                        "client_port": "2001"
                    },
                    "advertise": {
                        "address": "localhost",
                        "peer_port": "2000",
                        "client_port": "2001"
                    },
                    "cluster": {
                        "type": "init"
                    }
                }
            }, indent=4))
        with open("mongodb1/conf.json", "w") as f:
            f.write(json.dumps({
                "daemon": {
                    "retry": {
                        "times": 3,
                        "interval": 5
                    },
                    "etcd_path": {
                        "init": "mongodb/init",
                        "register": "mongodb/register/"
                    },
                    "raw_log_symbol_pos": 29,
                    "register_interval": 5,
                },
                "mongodb": {
                    "exe": "mongod",
                    "name": "mongodb1",
                    "data_dir": "mongodb1/mongodb",
                    "data_init_dir": "mongodb1/mongodb_init",
                    "listen": {
                        "address": "0.0.0.0",
                        "port": "3000"
                    },
                    "advertise": {
                        "address": "localhost",
                        "port": "3000"
                    },
                    "replica_set": "rs"
                }
            }, indent=4))
        with open("mongodb2/conf.json", "w") as f:
            f.write(json.dumps({
                "daemon": {
                    "retry": {
                        "times": 3,
                        "interval": 5
                    },
                    "etcd_path": {
                        "init": "mongodb/init",
                        "register": "mongodb/register/"
                    },
                    "raw_log_symbol_pos": 29,
                    "register_interval": 5,
                },
                "mongodb": {
                    "exe": "mongod",
                    "name": "mongodb2",
                    "data_dir": "mongodb2/mongodb",
                    "data_init_dir": "mongodb2/mongodb_init",
                    "listen": {
                        "address": "0.0.0.0",
                        "port": "3001"
                    },
                    "advertise": {
                        "address": "localhost",
                        "port": "3001"
                    },
                    "replica_set": "rs"
                }
            }, indent=4))
        with open("mongodb3/conf.json", "w") as f:
            f.write(json.dumps({
                "daemon": {
                    "retry": {
                        "times": 3,
                        "interval": 5
                    },
                    "etcd_path": {
                        "init": "mongodb/init",
                        "register": "mongodb/register/"
                    },
                    "raw_log_symbol_pos": 29,
                    "register_interval": 5,
                },
                "mongodb": {
                    "exe": "mongod",
                    "name": "mongodb3",
                    "data_dir": "mongodb3/mongodb",
                    "data_init_dir": "mongodb3/mongodb_init",
                    "listen": {
                        "address": "0.0.0.0",
                        "port": "3002"
                    },
                    "advertise": {
                        "address": "localhost",
                        "port": "3002"
                    },
                    "replica_set": "rs"
                }
            }, indent=4))

        # Sub processes
        cls.etcd_proc = multiprocessing.Process(target=etcd_run, args=("Etcd", "etcd/conf.json"))
        cls.etcd_proc.daemon = True
        cls.etcd_proc.start()
        cls.mongodb1 = None
        cls.mongodb2 = None
        cls.mongodb3 = None
        return

    def test_000_run_mongodb_daemon(self):
        """
        Test to run mongodb through mongodb daemon
        :return: None
        """
        cls = self.__class__

        time.sleep(10)

        # Generate all daemon
        cls.mongodb1 = multiprocessing.Process(target=run, args=("Mongodb1", "etcd/conf.json", "mongodb1/conf.json"))
        cls.mongodb1.daemon = True
        cls.mongodb1.start()
        cls.mongodb2 = multiprocessing.Process(target=run, args=("Mongodb2", "etcd/conf.json", "mongodb2/conf.json"))
        cls.mongodb2.daemon = True
        cls.mongodb2.start()
        cls.mongodb3 = multiprocessing.Process(target=run, args=("Mongodb3", "etcd/conf.json", "mongodb3/conf.json"))
        cls.mongodb3.daemon = True
        cls.mongodb3.start()

        time.sleep(20)

        # Test if every mongodb has joined the replica set
        cls.etcd = EtcdProxy("http://localhost:2001", get_logger("Test", None, None))
        registered_member = list(cls.etcd.get("mongodb/register/").values())
        cls.mongo1 = pymongo.MongoClient("localhost", 3000)
        cls.mongo1_rs = pymongo.MongoClient("localhost", 3000, replicaSet="rs")
        conf = cls.mongo1.admin.command("replSetGetConfig", 1)["config"]["members"]
        self.assertEqual(
            set([x["host"] for x in conf]),
            set(registered_member)
        )

        cls.mongo2 = pymongo.MongoClient("localhost", 3001)
        cls.mongo2_rs = pymongo.MongoClient("localhost", 3001, replicaSet="rs")
        cls.mongo3 = pymongo.MongoClient("localhost", 3002)
        cls.mongo3_rs = pymongo.MongoClient("localhost", 3002, replicaSet="rs")
        cls.res = cls.mongo2_rs.client["test_db"]["test_collection"].insert_one({"value": 0})
        self.assertEqual(
            cls.mongo1_rs.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
            0
        )
        self.assertEqual(
            cls.mongo3_rs.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
            0
        )
        return

    def test_001_stop_mongodb_daemon(self):
        """
        Test to stop mongodb through daemon
        :return: None
        """
        cls = self.__class__

        os.kill(cls.mongodb1.pid, signal.SIGINT)
        cls.mongodb1.join()
        time.sleep(15)
        self.assertEqual(
            set(list(cls.etcd.get("mongodb/register/").values())),
            set([x["host"] for x in cls.mongo2.admin.command("replSetGetConfig", 1)["config"]["members"]])
        )

        self.assertEqual(
            cls.mongo2_rs.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
            0
        )
        self.assertEqual(
            cls.mongo3_rs.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
            0
        )
        return

    @classmethod
    def tearDownClass(cls):
        """
        Cleaning function
        :return: None
        """
        print("Tearing down environment.\n")

        # Stop subprocess
        if cls.mongodb1 and cls.mongodb1.is_alive():
            if cls.mongodb1.pid:
                os.kill(cls.mongodb1.pid, signal.SIGINT)
            cls.mongodb1.join()
        if cls.mongodb2 and cls.mongodb2.is_alive():
            if cls.mongodb2.pid:
                os.kill(cls.mongodb2.pid, signal.SIGINT)
            cls.mongodb2.join()
        if cls.mongodb3 and cls.mongodb3.is_alive():
            if cls.mongodb3.pid:
                os.kill(cls.mongodb3.pid, signal.SIGINT)
            cls.mongodb3.join()
        if cls.etcd_proc and cls.etcd_proc.is_alive():
            if cls.etcd_proc.pid:
                os.kill(cls.etcd_proc.pid, signal.SIGINT)
            cls.etcd_proc.join()

        # Remove temp dir
        for d in ["mongodb1", "mongodb2", "mongodb3", "etcd"]:
            shutil.rmtree(d)
        return

if __name__ == "__main__":
    unittest.main()
