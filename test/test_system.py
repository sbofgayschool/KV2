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

from rpc.judicator_rpc.ttypes import *

from utility.etcd.daemon import run as etcd_run
from utility.mongodb.daemon import run as mongodb_run
from judicator.main import run as judicator_run
from executor.main import run as executor_run
from utility.task import TASK_STATUS


# A general task
task_template = {
    "user": 0,
    "compile_source_str": "bebebe\n",
    "compile_source_name": "sources",
    "compile_command": "cat sources;\necho 'compiled.';\n",
    "compile_timeout": 1,
    "execute_input": "",
    "execute_data_str": "nrnrnr\n",
    "execute_data_name": "raw.dat",
    "execute_command": "cat data/raw.dat;\necho 'executed.';\n",
    "execute_timeout": 1,
    "execute_standard": "std",
}

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
                    "interval": 10,
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
                    "expiration": 10
                },
                "executor": {
                    "database": "judicator",
                    "collection": "executor",
                    "expiration": 15
                },
            }, indent=4))
        with open("config/executor.json", "w") as f:
            f.write(json.dumps({
                "retry": {
                    "times": 3,
                    "interval": 5
                },
                "name": "executor",
                "data_dir": "data/executor",
                "judicator_etcd_path": "judicator/service",
                "task": {
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
        :return: None
        """
        time.sleep(10)

        self.assertEqual(requests.get("http://localhost:7000/api/test").text, "Khala gateway server is working.")
        return

    def test_001_add_search_get_cancel_task(self):
        """
        Test for adding a task without an executor. Then perform search, get and cancel.
        :return: None
        """
        # Try an invalid input
        task = dict(task_template)
        task["compile_timeout"] = -1
        self.assertEqual(
            json.loads(requests.post("http://localhost:7000/api/task", data=task).text),
            {"result": ReturnCode.INVALID_INPUT, "id": None}
        )

        # Try an valid input
        task["compile_timeout"] = 1
        res = json.loads(requests.post("http://localhost:7000/api/task", data=task).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        id = res["id"]

        # Now search
        param = {
            "user": 0,
            "start_time": "1900-01-01T00:00:00",
            "end_time": "2020-12-31T23:59:59",
            "limit": 10,
            "page": 0
        }
        res = json.loads(requests.get("http://localhost:7000/api/task/list", params=param).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["pages"], 1)
        self.assertEqual(len(res["tasks"]), 1)
        self.assertEqual(res["tasks"][0]["id"], id)

        # Get details
        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": id}).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["id"], id)
        self.assertEqual(res["task"]["status"], TASK_STATUS["PENDING"])
        self.assertEqual(res["task"]["executor"], None)

        # Cancel it
        self.assertEqual(
            json.loads(requests.delete("http://localhost:7000/api/task", params={"id": id}).text)["result"],
            ReturnCode.OK
        )
        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": id}).text)
        self.assertEqual(res["task"]["id"], id)
        self.assertEqual(res["task"]["status"], TASK_STATUS["CANCELLED"])

        return

    def test_002_start_executor_and_check(self):
        """
        Start an executor and check judicator and executor list.
        :return: None
        """
        cls = self.__class__

        cls.executor = multiprocessing.Process(
            target=executor_run,
            args=("Executor", "config/etcd.json", "config/executor.json")
        )
        cls.executor.daemon = True
        cls.executor.start()

        time.sleep(6)
        res = json.loads(requests.get("http://localhost:7000/api/judicators").text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["judicators"], [{"name": "/judicator/service/judicator", "address": "localhost:4000"}])

        res = json.loads(requests.get("http://localhost:7000/api/executors").text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(len(res["executors"]), 1)
        self.assertEqual(res["executors"][0]["hostname"], "executor")

    def test_003_add_tasks(self):
        """
        Test for adding different tasks
        :return: None
        """
        # Cancelled
        task = dict(task_template)
        task["compile_timeout"] = 100
        task["compile_command"] = "sleep 99"
        res = json.loads(requests.post("http://localhost:7000/api/task", data=task).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        cancel_id = res["id"]
        while True:
            time.sleep(1)
            res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": cancel_id}).text)
            self.assertEqual(res["result"], ReturnCode.OK)
            if res["task"]["executor"]:
                break
        self.assertEqual(
            json.loads(requests.delete("http://localhost:7000/api/task", params={"id": cancel_id}).text)["result"],
            ReturnCode.OK
        )
        time.sleep(1)
        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": cancel_id}).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["status"], TASK_STATUS["CANCELLED"])

        time.sleep(5)

        # Compile timeout
        task = dict(task_template)
        task["compile_command"] = "sleep 2"
        res = json.loads(requests.post("http://localhost:7000/api/task", data=task).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        compile_timeout_id = res["id"]

        # Execute timeout
        task = dict(task_template)
        task["execute_command"] = "sleep 2"
        res = json.loads(requests.post("http://localhost:7000/api/task", data=task).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        execute_timeout_id = res["id"]

        # Success but big output
        task = dict(task_template)
        task["execute_command"] = "echo '%s'" % ("a" * 1500)
        res = json.loads(requests.post("http://localhost:7000/api/task", data=task).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        truncate_id = res["id"]

        # Success
        res = json.loads(requests.post("http://localhost:7000/api/task", data=task_template).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        success_id = res["id"]

        time.sleep(11)

        # Check result
        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": compile_timeout_id}).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["status"], TASK_STATUS["COMPILE_FAILED"])
        self.assertEqual(res["task"]["result"]["compile_error"], "Compile time out.")
        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": execute_timeout_id}).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["status"], TASK_STATUS["RUN_FAILED"])
        self.assertEqual(res["task"]["result"]["execute_error"], "Execution time out.")
        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": truncate_id}).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["status"], TASK_STATUS["SUCCESS"])
        self.assertEqual(res["task"]["result"]["compile_output"], "a" * 1000 + "...")
        res = json.loads(
            requests.get("http://localhost:7000/api/task", params={"id": truncate_id, "no_truncate": "1"}).text
        )
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["status"], TASK_STATUS["SUCCESS"])
        self.assertEqual(res["task"]["result"]["compile_output"], "a" * 1500)
        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": success_id}).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["status"], TASK_STATUS["SUCCESS"])
        self.assertEqual(res["task"]["result"]["compile_output"], "bebebe\ncompiled.\n")
        self.assertEqual(res["task"]["result"]["execute_output"], "nrnrnr\nexecuted.\n")

        return

    def test_004_executor_exit(self):
        """
        # Test when executor exit
        :return: None
        """
        cls = self.__class__

        task = dict(task_template)
        task["compile_timeout"] = 100
        task["compile_command"] = "sleep 99"
        res = json.loads(requests.post("http://localhost:7000/api/task", data=task).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        id = res["id"]
        while True:
            time.sleep(1)
            res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": id}).text)
            self.assertEqual(res["result"], ReturnCode.OK)
            if res["task"]["executor"]:
                break

        time.sleep(1)

        os.kill(cls.executor.pid, signal.SIGINT)

        time.sleep(30)

        res = json.loads(requests.get("http://localhost:7000/api/task", params={"id": id}).text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(res["task"]["status"], TASK_STATUS["RETRYING"])
        self.assertEqual(res["task"]["executor"], None)
        res = json.loads(requests.get("http://localhost:7000/api/executors").text)
        self.assertEqual(res["result"], ReturnCode.OK)
        self.assertEqual(len(res["executors"]), 0)

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
