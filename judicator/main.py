# -*- encoding: utf-8 -*-

__author__ = "chenty"

import datetime
import threading
import time
import urllib.parse
from jsoncomment import JsonComment

from utility.function import get_logger, try_with_times
from utility.etcd import generate_local_etcd_proxy
from utility.mongodb import generate_local_mongodb_proxy
from utility.define import TASK_STATUS

from rpc.judicator_rpc import Judicator
from rpc.judicator_rpc.ttypes import *
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

json = JsonComment()


def register():
    logger.info("Register thread start to work.")
    reg_key = urllib.parse.urljoin(config["register"]["etcd_path"], config["name"])
    reg_value = config["advertise"]["address"] + ":" + config["advertise"]["port"]
    while True:
        time.sleep(config["register"]["interval"])
        try:
            local_etcd.set(reg_key, reg_value, ttl=config["register"]["ttl"])
            logger.info("Updated judicator service on etcd.")
        except:
            logger.error("Failed to update judicator service on etcd.", exc_info=True)

def lead():
    logger.info("Lead thread start to work.")
    while True:
        time.sleep(config["lead"]["interval"])
        try:
            local_etcd.set(
                config["lead"]["etcd_path"],
                config["name"],
                ttl=config["lead"]["ttl"],
                insert=True
            )
            logger.info("No previous leader. This node has become leader.")
        except:
            logger.warn("Previous leader exists.", exc_info=True)
        try:
            local_etcd.set(
                config["lead"]["etcd_path"],
                config["name"],
                ttl=config["lead"]["ttl"],
                prev_value=config["name"]
            )
            success = True
            logger.info("Successfully update leader information.")
        except:
            success = False
            logger.warn("Failed to become leader.", exc_info=True)
        if success:
            logger.info("This node is leader, starting routine check of tasks and executors.")
            expire_time = datetime.datetime.now() - datetime.timedelta(seconds=config["task"]["expiration"])
            while True:
                res = mongodb_task.find_one_and_update(
                    {"done": False, "executor": {"$exists": True}, "report_time": {"$ls": expire_time}},
                    {"$unset": {"executor": ""}, "$set": {"status": TASK_STATUS["RETRYING"]}}
                )
                if not res:
                    break
                logger.warn("Set expired task %s into retrying status." % str(res["_id"]))

            expire_time = datetime.datetime.now() - datetime.timedelta(seconds=config["executor"]["expiration"])
            while True:
                res = mongodb_executor.find_one_and_delete({"report_time": {"$ls": expire_time}})
                if not res:
                    break
                logger.warn("Delete expired executor %s from records." % str(res["_id"]))

            logger.info("Finished routine check.")

class RPCService:
    def __init__(self, logger):
        self.logger = logger
        return

    # TODO: Work with rpc interfaces.

if __name__ == "__main__":
    with open("config/main.json", "r") as f:
        config = json.load(f)
    retry_times = config["retry"]["times"]
    retry_interval = config["retry"]["interval"]

    if "log" in config:
        logger = get_logger(
            "main",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("main", None, None)

    with open("config/etcd.json", "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)
    with open("config/mongodb.json", "r") as f:
        local_mongodb = generate_local_mongodb_proxy(json.load(f)["mongodb"], logger)
    mongodb_task = local_mongodb.client[config["task"]["database"]][config["task"]["collection"]]
    mongodb_executor = local_mongodb.client[config["executor"]["database"]][config["executor"]["collection"]]

    register_thread = threading.Thread(target=register)
    register_thread.setDaemon(True)
    register_thread.start()

    lead_thread = threading.Thread(target=lead)
    lead_thread.setDaemon(True)
    lead_thread.start()

    handler = RPCService(logger)
    processor = Judicator.Processor(handler)
    transport = TSocket.TServerSocket(config["listen"]["address"], int(config["listen"]["port"]))
    tfactory = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()
    server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)
    try:
        logger.info("RPC server start to serve.")
        server.serve()
    except:
        logger.error("Accidentally terminated. Killing etcd process.", exc_info=True)
    logger.info("Exiting.")