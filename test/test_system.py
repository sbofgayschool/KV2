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