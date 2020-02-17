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

from utility.etcd.proxy import etcd_generate_run_command, generate_local_etcd_proxy, EtcdProxy
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
        # Generate config
        cls.infra0_conf = {
            "exe": "etcd",
            "name": "infra0",
            "data_dir": "infra0",
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
        cls.infra1_conf = {
            "exe": "etcd",
            "name": "infra1",
            "data_dir": "infra1",
            "listen": {
                "address": "0.0.0.0",
                "peer_port": "2002",
                "client_port": "2003"
            },
            "advertise": {
                "address": "localhost",
                "peer_port": "2002",
                "client_port": "2003"
            },
            "cluster": {
                "type": "join",
                "client": "http://localhost:2001"
            }
        }
        cls.infra2_conf = {
            "exe": "etcd",
            "name": "infra2",
            "data_dir": "infra2",
            "proxy": "on",
            "listen": {
                "address": "0.0.0.0",
                "peer_port": "2004",
                "client_port": "2005"
            },
            "advertise": {
                "address": "localhost",
                "peer_port": "2004",
                "client_port": "2005"
            },
            "cluster": {
                "type": "join",
                "client": "http://localhost:2001"
            }
        }
        cls.infra0_proc = None
        cls.infra1_proc = None
        cls.infra2_proc = None

        # Generate temp data dir
        for d in ["infra0", "infra1", "infra2"]:
            os.mkdir(d)

        # Generate a logger
        cls.logger = get_logger("Test", None, None)
        return

    def test_000_independent_init(self):
        """
        Test independent init
        :return: None
        """
        cls = self.__class__

        cls.infra0_proc = subprocess.Popen(
            etcd_generate_run_command(cls.infra0_conf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        cls.infra0 = generate_local_etcd_proxy(cls.infra0_conf, cls.logger)
        self.assertEqual(cls.infra0.url, "http://localhost:2001")
        return

    def test_001_get_self_status(self):
        """
        Test get self status
        :return: None
        """
        time.sleep(5)

        cls = self.__class__
        self.assertEqual(cls.infra0.get_self_status() is not None, True)
        return

    def test_002_add_and_get_members(self):
        """
        Test add and get member through proxy
        :return: None
        """
        cls = self.__class__
        self.assertEqual(
            cls.infra0.add_and_get_members(None, None),
            {"infra0": "http://localhost:2000"}
        )

        # Join the cluster by adding self information
        res = cls.infra0.add_and_get_members("infra1", "http://localhost:2002", False)
        self.assertEqual(res, {"infra0": "http://localhost:2000", "infra1": "http://localhost:2002"})
        # Generate member argument for the joining command
        cls.infra1_conf["cluster"]["member"] = ",".join([(k + "=" + v) for k, v in res.items()])
        cls.infra1_proc = subprocess.Popen(
            etcd_generate_run_command(cls.infra1_conf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        cls.infra1 = generate_local_etcd_proxy(cls.infra1_conf, cls.logger)

        time.sleep(5)

        # The same thing but for proxy mode
        res = cls.infra1.add_and_get_members("infra1", "http://localhost:2002", True)
        self.assertEqual(res, {"infra0": "http://localhost:2000", "infra1": "http://localhost:2002"})
        cls.infra2_conf["cluster"]["member"] = ",".join([(k + "=" + v) for k, v in res.items()])
        cls.infra2_proc = subprocess.Popen(
            etcd_generate_run_command(cls.infra2_conf),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        cls.infra2 = generate_local_etcd_proxy(cls.infra2_conf, cls.logger)

        time.sleep(5)

        # Check if everything is expected
        self.assertEqual(
            cls.infra2.add_and_get_members(None, None),
            {"infra0": "http://localhost:2000", "infra1": "http://localhost:2002"}
        )
        return

    def test_003_set_get_delete(self):
        """
        Test for set, get and delete key-value pair on etcd
        :return: None
        """
        cls = self.__class__

        # Set value with different condition
        cls.infra0.set("k", "v")
        with self.assertRaises(Exception):
            cls.infra1.set("k", "value", insert=True)
        cls.infra2.set("key", "value", insert=True)

        self.assertEqual(self.infra0.get("k"), "v")
        self.assertEqual(self.infra1.get("key"), "value")

        with self.assertRaises(Exception):
            cls.infra2.set("key", "new value", prev_value="?")
        cls.infra0.set("key", "new value", prev_value="value")
        cls.infra1.set("temp key", "temp value", ttl=3)
        cls.infra2.set("dir/k1", "v1")
        cls.infra0.set("dir/k2", "v2")

        self.assertEqual(cls.infra2.get("key"), "new value")
        self.assertEqual(cls.infra0.get("temp key"), "temp value")
        self.assertEqual(cls.infra1.get("dir"), {"/dir/k1": "v1", "/dir/k2": "v2"})

        time.sleep(5)

        with self.assertRaises(Exception):
            cls.infra0.delete("key", prev_value="?")
        cls.infra2.delete("key")
        with self.assertRaises(Exception):
            cls.infra0.delete("key")

        self.assertEqual(cls.infra1.get("temp key"), None)
        with self.assertRaises(Exception):
            cls.infra2.get("key", none_if_empty=False)

        return


    def test_004_remove_member(self):
        """
        Test for removing a cluster member
        :return: None
        """
        cls = self.__class__

        # Remove member in different conditions
        cls.infra1.remove_member("infra0", "http://localhost:2002")
        self.assertEqual(
            cls.infra2.add_and_get_members(None, None),
            {"infra0": "http://localhost:2000", "infra1": "http://localhost:2002"}
        )

        cls.infra1.remove_member("infra0", "http://localhost:2000")
        time.sleep(5)
        self.assertEqual(
            cls.infra2.add_and_get_members(None, None),
            {"infra1": "http://localhost:2002"}
        )

        return

    @classmethod
    def tearDownClass(cls):
        """
        Cleaning function
        :return: None
        """
        print("Tearing down environment.\n")
        # Kill a subprocess
        if cls.infra0_proc:
            os.kill(cls.infra0_proc.pid, signal.SIGKILL)
            cls.infra0_proc.wait()
        if cls.infra1_proc:
            os.kill(cls.infra1_proc.pid, signal.SIGKILL)
            cls.infra1_proc.poll()
        if cls.infra2_proc:
            os.kill(cls.infra2_proc.pid, signal.SIGKILL)
            cls.infra2_proc.poll()

        # Discarded test of tracemalloc
        # f = open("__init__.py", "r")

        # Remove temp dir
        for d in ["infra0", "infra1", "infra2"]:
            shutil.rmtree(d)
        return

if __name__ == "__main__":
    unittest.main()
