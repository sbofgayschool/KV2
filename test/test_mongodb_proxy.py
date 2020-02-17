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
import subprocess
import signal
import time
import shutil
import tracemalloc
tracemalloc.start()

from utility.mongodb.proxy import generate_local_mongodb_proxy, mongodb_generate_run_command
from utility.etcd.proxy import etcd_generate_run_command, EtcdProxy
from utility.function import get_logger


# Unit test class for utility.etcd.proxy
class TestEtcdProxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Initialization function
        :return: None
        """
        print("Initializing environment.\n")

        # Generate temp data dir
        for d in ["etcd", "mongodb1", "mongodb2", "mongodb3"]:
            os.mkdir(d)

        # Generate etcd
        etcd_conf = {
            "exe": "etcd",
            "name": "etcd",
            "data_dir": "etcd",
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
        cls.etcd_proc = subprocess.Popen(
            etcd_generate_run_command(etcd_conf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # Generate mongodb configuration
        cls.mongodb1_conf = {
            "exe": "mongod",
            "name": "mongodb1",
            "data_dir": "mongodb1",
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
        cls.mongodb2_conf = {
            "exe": "mongod",
            "name": "mongodb2",
            "data_dir": "mongodb2",
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
        cls.mongodb3_conf = {
            "exe": "mongod",
            "name": "mongodb3",
            "data_dir": "mongodb3",
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
        cls.init_key = "mongodb/init"
        cls.reg_path = "mongodb/register/"

        cls.mongodb1_proc = None
        cls.mongodb2_proc = None
        cls.mongodb3_proc = None

        # Generate a logger and etcd proxy
        cls.logger = get_logger("Test", None, None)
        cls.etcd = EtcdProxy("http://localhost:2001", cls.logger)
        return

    def test_000_check(self):
        """
        Test for starting up and checking mongodb status
        :return: None
        """
        cls = self.__class__

        # Start all mongodb proxy
        cls.mongodb1_proc = subprocess.Popen(
            mongodb_generate_run_command(cls.mongodb1_conf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        cls.mongodb2_proc = subprocess.Popen(
            mongodb_generate_run_command(cls.mongodb2_conf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        cls.mongodb3_proc = subprocess.Popen(
            mongodb_generate_run_command(cls.mongodb3_conf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        cls.mongodb1 = generate_local_mongodb_proxy(cls.mongodb1_conf, cls.etcd, cls.logger)
        cls.mongodb2 = generate_local_mongodb_proxy(cls.mongodb2_conf, cls.etcd, cls.logger)
        cls.mongodb3 = generate_local_mongodb_proxy(cls.mongodb3_conf, cls.etcd, cls.logger)

        time.sleep(5)
        self.assertEqual(cls.mongodb1.check(), True)
        self.assertEqual(cls.mongodb2.check(), True)
        self.assertEqual(cls.mongodb3.check(), True)

    def test_001_init_join(self):
        """
        Test for initializing a replica set and joining it
        :return: None
        """
        cls = self.__class__

        # Initialize mongodb
        cls.mongodb1.initialize(cls.init_key, cls.reg_path)
        cls.mongodb2.initialize(cls.init_key, cls.reg_path)
        cls.mongodb3.initialize(cls.init_key, cls.reg_path)

        self.assertEqual(cls.etcd.get(cls.init_key), "localhost:3000")
        self.assertEqual(
            cls.etcd.get(cls.reg_path),
            {
                "/" + cls.reg_path + "mongodb1": "localhost:3000",
                "/" + cls.reg_path + "mongodb2": "localhost:3001",
                "/" + cls.reg_path + "mongodb3": "localhost:3002"
            }
        )
        return

    def test_002_adjust_replica_set_is_primary(self):
        """
        Test for adjusting replica set and checking primary state
        :return: None
        """
        cls = self.__class__
        registered_member = list(cls.etcd.get(cls.reg_path).values())

        # Check primary state and adjust replica set
        time.sleep(5)
        self.assertEqual(cls.mongodb1.is_primary(), True)
        cls.mongodb1.adjust_replica_set(registered_member)

        time.sleep(5)

        # Newly added node should be in secondary state without vote weight
        self.assertEqual(cls.mongodb2.is_primary(), False)
        self.assertEqual(cls.mongodb3.is_primary(), False)
        conf = cls.mongodb1.local_client.admin.command("replSetGetConfig", 1)["config"]["members"]
        self.assertEqual(
            set([x["host"] for x in conf]),
            set(registered_member)
        )
        self.assertEqual(sum([x.get("votes", 0) for x in conf]), 1)

        # Adjust again to give them weights
        cls.mongodb1.adjust_replica_set(registered_member)
        time.sleep(1)
        conf = cls.mongodb1.local_client.admin.command("replSetGetConfig", 1)["config"]["members"]
        self.assertEqual(sum([x.get("votes", 0) for x in conf]), 3)
        return

    def test_003_db_operation(self):
        """
        Test for carrying out normal db operations
        :return: None
        """
        cls = self.__class__

        # Do something to the db
        cls.res = cls.mongodb2.client["test_db"]["test_collection"].insert_one({"value": 0})
        self.assertEqual(
            cls.mongodb1.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
            0
        )
        self.assertEqual(
            cls.mongodb3.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
            0
        )
        return

    def test_004_cancel_registration_and_shutdown(self):
        """
        test for cancelling registration on etcd and shutting down mongodb
        :return: None
        """
        cls = self.__class__

        # Shut the primary down and check if there will be a primary soon
        cls.mongodb1.cancel_registration(cls.reg_path)
        self.assertEqual(
            cls.etcd.get(cls.reg_path),
            {
                "/" + cls.reg_path + "mongodb2": "localhost:3001",
                "/" + cls.reg_path + "mongodb3": "localhost:3002"
            }
        )
        self.assertEqual(cls.mongodb1.shutdown_and_close(), True)
        time.sleep(10)
        self.assertEqual(cls.mongodb2.is_primary() ^ cls.mongodb3.is_primary(), True)

        # Remove mongodb1 from replica set
        new_primary = cls.mongodb2 if cls.mongodb2.is_primary() else cls.mongodb3
        registered_member = list(cls.etcd.get(cls.reg_path).values())
        new_primary.adjust_replica_set(registered_member)
        time.sleep(1)
        conf = new_primary.local_client.admin.command("replSetGetConfig", 1)["config"]["members"]
        self.assertEqual(
            set([x["host"] for x in conf]),
            set(registered_member)
        )

        # Everything should still work
        self.assertEqual(
            cls.mongodb2.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
            0
        )
        self.assertEqual(
            cls.mongodb3.client["test_db"]["test_collection"].find_one({"_id": cls.res.inserted_id})["value"],
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

        # Kill subprocess
        if cls.mongodb1_proc:
            os.kill(cls.mongodb1_proc.pid, signal.SIGKILL)
            cls.mongodb1_proc.wait()
        if cls.mongodb2_proc:
            os.kill(cls.mongodb2_proc.pid, signal.SIGKILL)
            cls.mongodb2_proc.wait()
        if cls.mongodb3_proc:
            os.kill(cls.mongodb3_proc.pid, signal.SIGKILL)
            cls.mongodb3_proc.wait()
        if cls.etcd_proc:
            os.kill(cls.etcd_proc.pid, signal.SIGKILL)
            cls.etcd_proc.wait()

        # Remove temp dir
        for d in ["etcd", "mongodb1", "mongodb2", "mongodb3"]:
            shutil.rmtree(d)
        return

if __name__ == "__main__":
    unittest.main()
