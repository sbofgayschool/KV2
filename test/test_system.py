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
import shutil
import requests
import json
import tracemalloc
tracemalloc.start()

from utility.etcd.daemon import run as etcd_run
from utility.mongodb.daemon import run as mongodb_run
from judicator.main import run as judicator_run
from executor.main import run as executor_run


# Unit test class for a integrated system
class TestSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Initialization function
        :return: None
        """
        print("Initializing environment.\n")

        # Generate all dirs
        for d in [
            "data",
            "data/etcd",
            "data/etcd_init",
            "data/mongodb",
            "data/mongodb_init",
            "data/judicator",
            "data/executor",
            "data/gateway",
            "config"
        ]:
            os.mkdir(d)
        # Generate configuration files
        with open("config/etcd.json", "w") as f:
            f.write(json.dumps({
                "daemon": {
                    "retry": {
                        "times": 3,
                        "interval": 5
                    },
                    "raw_log_symbol_pos": 27
                },
                "etcd": {
                    "exe": "etcd",
                    "name": "etcd",
                    "data_dir": "data/etcd",
                    "data_init_dir": "data/etcd_init",
                    "strict_reconfig": True,
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
        with open("config/mongodb.json", "w") as f:
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
                    "name": "mongodb",
                    "data_dir": "data/mongodb",
                    "data_init_dir": "data/mongodb_init",
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
        with open("config/judicator.json", "w") as f:
            f.write(json.dumps({
                "retry": {
                    "times": 3,
                    "interval": 5
                },
                "name": "judicator",
                "listen": {
                    "address": "0.0.0.0",
                    "port": "4000"
                },
                "advertise": {
                    "address": "localhost",
                    "port": "4000"
                },
                "lead": {
                    "etcd_path": "judicator/leader",
                    "interval": 20,
                    "ttl": 45
                },
                "register": {
                    "etcd_path": "judicator/service/",
                    "interval": 5,
                    "ttl": 12
                },
                "task": {
                    "database": "judicator",
                    "collection": "task",
                    "expiration": 30
                },
                "executor": {
                    "database": "judicator",
                    "collection": "executor",
                    "expiration": 40
                },
            }, indent=4))
        with open("config/executor.json", "w") as f:
            f.write(json.dumps({
                "retry": {
                    "times": 3,
                    "interval": 5
                },
                "name": "executor_main",
                "data_dir": "data/executor",
                "judicator_etcd_path": "judicator/service",
                "task": {
                    "user": {
                        "uid": 501,
                        "gid": 20
                    },
                    "vacant": 3,
                    "dir": {
                        "download": "download",
                        "source": "source",
                        "data": "source/data",
                        "result": "result"
                    },
                    "compile": {
                        "source": "source.zip",
                        "command": "compile.sh",
                        "output": "compile.out",
                        "error": "compile.err"
                    },
                    "execute": {
                        "input": "execute.in",
                        "data": "source.zip",
                        "command": "execute.sh",
                        "output": "execute.out",
                        "error": "execute.err"
                    }
                },
                "report_interval": 5,
            }, indent=4))
        with open("config/uwsgi.json", "w") as f:
            f.write(json.dumps({
                "server": {
                    "judicator_etcd_path": "judicator/service",
                    "template": "../gateway/webpage",
                    "data_dir": "data/gateway"
                }
            }, indent=4))

        # Sub processes
        cls.etcd = multiprocessing.Process(target=etcd_run, args=("Etcd", "config/etcd.json"))
        cls.etcd.daemon = True
        cls.etcd.start()
        time.sleep(5)
        cls.mongodb = multiprocessing.Process(
            target=mongodb_run,
            args=("Mongodb", "config/etcd.json", "config/mongodb.json")
        )
        cls.mongodb.daemon = True
        cls.mongodb.start()
        time.sleep(5)
        cls.judicator = multiprocessing.Process(
            target=judicator_run,
            args=("Judicator", "config/etcd.json", "config/mongodb.json", "config/judicator.json")
        )
        cls.judicator.daemon = True
        cls.judicator.start()
        from gateway.server import server
        cls.gateway = multiprocessing.Process(
            target=server.run,
            args=("localhost", 7000),
            kwargs={"threaded": True}
        )
        cls.gateway.daemon = True
        cls.gateway.start()
        cls.executor = None

        return

    def test_000_system_working(self):
        """
        Test that the system is working through
        :return:
        """
        time.sleep(5)

        self.assertEqual(requests.get("http://localhost:7000/api/test").text, "Khala gateway server is working.")
        return

    @classmethod
    def tearDownClass(cls):
        """
        Cleaning function
        :return: None
        """
        print("Tearing down environment.\n")

        # Stop subprocess
        if cls.gateway and cls.gateway.is_alive():
            if cls.gateway.pid:
                os.kill(cls.gateway.pid, signal.SIGINT)
            cls.gateway.join()
        if cls.executor and cls.executor.is_alive():
            if cls.executor.pid:
                os.kill(cls.executor.pid, signal.SIGINT)
            cls.executor.join()
        if cls.judicator and cls.judicator.is_alive():
            if cls.judicator.pid:
                os.kill(cls.judicator.pid, signal.SIGINT)
            cls.judicator.join()
        if cls.mongodb and cls.mongodb.is_alive():
            if cls.mongodb.pid:
                os.kill(cls.mongodb.pid, signal.SIGINT)
            cls.mongodb.join()
        if cls.etcd and cls.etcd.is_alive():
            if cls.etcd.pid:
                os.kill(cls.etcd.pid, signal.SIGINT)
            cls.etcd.join()

        # Remove temp dir
        shutil.rmtree("config")
        shutil.rmtree("data")
        return

if __name__ == "__main__":
    unittest.main()
