# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
import datetime
import threading
import time
import urllib.parse
import dateutil
import pymongo
from bson.objectid import ObjectId

from utility.function import get_logger, try_with_times
from utility.etcd import generate_local_etcd_proxy
from utility.mongodb import generate_local_mongodb_proxy, transform_id
from utility.define import TASK_STATUS
from utility.rpc import extract, generate

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
                    {"done": False, "executor": {"$ne": None}, "report_time": {"$ls": expire_time}},
                    {"$set": [{"executor": None}, {"status": TASK_STATUS["RETRYING"]}]}
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

    def ping(self):
        return ReturnCode.OK

    def add(self, task):
        task = extract(task, result=False)
        del task["id"]
        task["done"] = False
        task["status"] = TASK_STATUS["PENDING"]
        task["report_time"] = datetime.datetime.now()
        try:
            mongodb_task.insert_one(task)
            return ReturnCode.OK
        except:
            return ReturnCode.ERROR

    def cancel(self, id):
        result = mongodb_task.find_one_and_update(
            {"_id": ObjectId(id), "done": False},
            {"executor": None, "status": TASK_STATUS["CANCEL"], "done": True}
        )
        if result:
            return ReturnCode.OK
        return ReturnCode.ERROR

    def search(self, id, start_time, end_time, old_to_new, limit):
        filter = {}
        if id:
            filter["id"] = {"$regex": "*" + id + "*"}
        if start_time or end_time:
            filter["time"] = {}
            if start_time:
                filter["time"]["$gt"] = dateutil.parser.parse(start_time)
            if end_time:
                filter["time"]["$ls"] = dateutil.parser.parse(end_time)
        result = mongodb_task.find(
            filter=filter,
            sort="report_time",
            limit=limit if limit else 0).sort("report_time", pymongo.ASCENDING if old_to_new else pymongo.DESCENDING)
        for r in result:
            transform_id(r)
        return SearchReturn(ReturnCode.OK, [generate(r, brief=True) for r in result])

    def get(self, id):
        result = mongodb_task.find_one({"_id": ObjectId(id)})
        if result:
            transform_id(result)
            return GetReturn(ReturnCode.OK, generate(result))
        return GetReturn(ReturnCode.NOT_EXIST, None)

    def report(self, executor, complete, executing, vacant):
        delete_list, assign_list = [], []
        result = mongodb_executor.find_one_and_update({"hostname": executor}, {"report_time": datetime.datetime.now()})
        if not result:
            mongodb_executor.insert({"hostname": executor, "report_time": datetime.datetime.now()})
        for t in complete:
            task = extract(t)
            mongodb_task.find_one_and_update(
                {"id": ObjectId(task["id"]), "executor": executor},
                {
                    "done": True,
                    "status": task["status"],
                    "executor": None,
                    "report_time": datetime.datetime.now(),
                    "result": task["result"]
                }
            )
            delete_list.append(generate(task, brief=True))
        for t in executing:
            task = extract(t, brief=True)
            result = mongodb_task.find_one_and_update(
                {"id": ObjectId(task["id"]), "executor": executor},
                {"status": task["status"], "report_time": datetime.datetime.now()}
            )
            if not result:
                delete_list.append(generate(task, brief=True))
        while vacant:
            task = mongodb_task.find_one_and_update(
                {"done": False, "executor": None},
                {"executor": executor, "report_time": datetime.datetime.now()},
                return_document=pymongo.ReturnDocument.AFTER
            )
            if not task:
                break
            transform_id(task)
            assign_list.append(generate(task))
            vacant = vacant - 1
        return ReportReturn(ReturnCode.OK, delete_list, assign_list)

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

    server = TServer.TThreadedServer(
        Judicator.Processor(RPCService(logger)),
        TSocket.TServerSocket(config["listen"]["address"], int(config["listen"]["port"])),
        TTransport.TBufferedTransportFactory(),
        TBinaryProtocol.TBinaryProtocolFactory()
    )
    try:
        logger.info("RPC server start to serve.")
        server.serve()
    except:
        logger.error("Accidentally terminated.", exc_info=True)
    logger.info("Exiting.")
