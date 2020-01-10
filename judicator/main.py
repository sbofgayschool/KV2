# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import datetime
import threading
import time
import urllib.parse
import dateutil
import pymongo
from bson.objectid import ObjectId
import dateutil.parser

from rpc.judicator_rpc import Judicator
from rpc.judicator_rpc.ttypes import *
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from utility.function import get_logger
from utility.etcd import generate_local_etcd_proxy
from utility.mongodb import generate_local_mongodb_proxy, transform_id
from utility.define import TASK_STATUS
from utility.rpc import extract, generate


def register():
    """
    Target function for register thread
    Regularly register the rpc service address in etcd
    :return: None
    """
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
    """
    Target function for lead thread
    Compete against others to be leader, and, if become the leader, do regular check of tasks and executors
    :return: None
    """
    logger.info("Lead thread start to work.")
    while True:
        time.sleep(config["lead"]["interval"])

        try:
            # Try to become leader when there are no previous leader
            try:
                local_etcd.set(
                    config["lead"]["etcd_path"],
                    config["name"],
                    ttl=config["lead"]["ttl"],
                    insert=True
                )
                logger.info("No previous leader. This node has become leader.")
            except:
                logger.warning("Previous leader exists.", exc_info=True)
            # Try to fresh the leader information, if the this is the leader
            # Set success to True if this successfully become the leader
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
                logger.warning("Failed to become leader.", exc_info=True)

            # If this is the leader, do regular check
            if success:
                logger.info("This node is leader, starting routine check of tasks and executors.")

                # Set all expired task to retrying and remove their executor
                expire_time = datetime.datetime.now() - datetime.timedelta(seconds=config["task"]["expiration"])
                while True:
                    res = mongodb_task.find_one_and_update(
                        {"done": False, "executor": {"$ne": None}, "report_time": {"$lt": expire_time}},
                        {"$set": {"executor": None, "status": TASK_STATUS["RETRYING"]}}
                    )
                    if not res:
                        break
                    logger.warning("Set expired task %s into retrying status." % str(res["_id"]))

                # Remove all expired executor from the record
                # Currently this is only for monitor usage
                expire_time = datetime.datetime.now() - datetime.timedelta(seconds=config["executor"]["expiration"])
                while True:
                    res = mongodb_executor.find_one_and_delete({"report_time": {"$lt": expire_time}})
                    if not res:
                        break
                    logger.warning("Delete expired executor %s from records." % res["hostname"])

                logger.info("Finished routine check.")
        except:
            logger.error("Error occurs during lead process.", exc_info=True)

class RPCService:
    """
    RPC handler class
    """
    def __init__(self, logger, mongodb_task, mongodb_executor):
        """
        Initializer of the class
        :param logger: The logger
        """
        self.logger = logger
        self.mongodb_task = mongodb_task
        self.mongodb_executor = mongodb_executor
        return

    def ping(self):
        """
        Interface: Ping
        Check whether the service is on
        :return: Always OK
        """
        self.logger.debug("Received RPC request: Ping.")
        return ReturnCode.OK

    def add(self, task):
        """
        Interface: Add
        Add a new task
        :param task: Task struture, the task needed to be added
        :return: An AddResult structure containing the result and the generated id of the new task
        """
        self.logger.debug("Received RPC request: Add.")

        # Extract and clean the task
        task = extract(task, result=False)
        del task["id"]
        task["add_time"] = datetime.datetime.now()
        task["done"] = False
        task["status"] = TASK_STATUS["PENDING"]
        task["report_time"] = datetime.datetime.now()
        self.logger.info("Adding new task to database: %s." % str(task))

        # Add and return the auto generated id
        try:
            result = self.mongodb_task.insert_one(task)
            return AddReturn(ReturnCode.OK, str(result.inserted_id))
        except:
            self.logger.error("Failed to insert task.", exc_info=True)
            return AddReturn(ReturnCode.ERROR, None)

    def cancel(self, id):
        """
        Interface: Cancel
        Cancel a Task which has not been done
        :param id: The id of the job neede to be cancelled
        :return: Whether the cancellation is successful
        """
        self.logger.debug("Received RPC request: Cancel.")
        self.logger.info("Task %s is going to be cancelled." % id)

        # Try to update the status and executor of a undone task
        result = self.mongodb_task.find_one_and_update(
            {"_id": ObjectId(id), "done": False},
            {"$set": {"executor": None, "status": TASK_STATUS["CANCELLED"], "done": True}}
        )
        if result:
            return ReturnCode.OK
        return ReturnCode.NOT_EXIST

    def search(self, id, user, start_time, end_time, old_to_new, limit, page):
        """
        Interface: Search
        Search tasks according to conditions
        :param id: Exact id of a task
        :param user: Exact user id of a task
        :param start_time: Start time of tasks
        :param end_time: End time of tasks
        :param old_to_new: If the result should be sorted in old-to-new order
        :param limit: Limitation of the total amount
        :param page: Page number of the search
        :return: A SearchReturn structure containing the result and all
        """
        self.logger.debug("Received RPC request: Search.")

        # Add conditions to the filter
        filter = {}
        if id:
            filter["_id"] = ObjectId(id)
        if user is not None:
            filter["user"] = user
        if start_time or end_time:
            filter["add_time"] = {}
            if start_time:
                filter["add_time"]["$gte"] = dateutil.parser.parse(start_time)
            if end_time:
                filter["add_time"]["$lte"] = dateutil.parser.parse(end_time)
        self.logger.debug("Filter: %s." % filter)

        # Count result first for page calculation later
        cnt = self.mongodb_task.count(filter=filter)
        # If nothing found, return directly
        if cnt == 0:
            self.logger.info("Find nothing.")
            return SearchReturn(ReturnCode.OK, 0, [])

        # Find all result and transform them into TaskBrief structure
        result = self.mongodb_task.find(
            filter=filter,
            sort=[(
                "add_time",
                pymongo.ASCENDING if old_to_new else pymongo.DESCENDING
            )],
            skip=(page if page else 0) * (limit if limit else 0),
            limit=(limit if limit else 0)
        )
        # Convert Cursor object to a list
        result = [x for x in result]
        for r in result:
            transform_id(r)
        self.logger.debug("Search result: %s." % result)
        return SearchReturn(
            ReturnCode.OK,
            1 if not limit else (cnt // limit + (1 if cnt % limit else 0)),
            [generate(r, brief=True) for r in result]
        )

    def get(self, id):
        """
        Interface: Get
        Get a specific task by id
        :param id: The id of the task
        :return: A GetResult structure containing return code and the task
        """
        self.logger.debug("Received RPC request: Get.")
        self.logger.info("Search for task %s." % id)

        # Find and transform the result
        result = self.mongodb_task.find_one({"_id": ObjectId(id)})
        self.logger.debug("Search result: %s." % str(result))
        if result:
            transform_id(result)
            return GetReturn(ReturnCode.OK, generate(result))
        return GetReturn(ReturnCode.NOT_EXIST, None)

    def report(self, executor, complete, executing, vacant):
        """
        Interface: Report
        Accept report from an executor, update corresponding information, and assign new task to the executor
        :param executor: Reporting executor
        :param complete: Completed tasks of the executor
        :param executing: Executing tasks
        :param vacant: Vacant place of the executor
        :return: A ReportResult structure containing return code, tasks needed to be deleted, and assigned tasks
        """
        self.logger.debug("Received RPC request: Report.")
        self.logger.info("Reporting executor: %s." % executor)

        # Refresh or add the information of the executor
        result = self.mongodb_executor.find_one_and_update(
            {"hostname": executor},
            {"$set": {"report_time": datetime.datetime.now()}}
        )
        if not result:
            self.mongodb_executor.insert_one({"hostname": executor, "report_time": datetime.datetime.now()})
        self.logger.info("Executor %s updated." % executor)

        delete_list, assign_list = [], []
        executing_list = []
        # Update all completed tasks, if the task indeed belong to the executor, and request the executor to delete it
        for t in complete:
            task = extract(t)
            self.logger.debug("Complete task: %s" % task)
            result = self.mongodb_task.find_one_and_update(
                {"_id": ObjectId(task["id"]), "executor": executor},
                {
                    "$set": {
                        "done": True,
                        "status": task["status"],
                        "executor": None,
                        "report_time": datetime.datetime.now(),
                        "result": task["result"]
                    }
                }
            )
            if not result:
                self.logger.warning("Complete task %s not found, delete it." % task["id"])
            else:
                self.logger.info("Successfully update complete task %s." % task["id"])
            # Complete task is going to be deleted, no matter whether there is such a task record
            delete_list.append(generate(task, brief=True))

        # Update all executing tasks, and request the executor to delete it if the task does not belong to it
        for t in executing:
            task = extract(t, brief=True)
            executing_list.append(ObjectId(task["id"]))
            self.logger.debug("Executing task %s." % task)
            result = self.mongodb_task.find_one_and_update(
                {"_id": ObjectId(task["id"]), "executor": executor},
                {"$set": {"status": task["status"], "report_time": datetime.datetime.now()}}
            )
            if not result:
                delete_list.append(generate(task, brief=True))
                self.logger.warning("Executing task %s not found, delete it." % task["id"])
            else:
                self.logger.info("Successfully update executing task %s." % task["id"])

        # Find all tasks which should be executed by this executor but not appear in executing list
        # And set them to retry
        self.logger.debug("Checking for unreported tasks.")
        while True:
            task = mongodb_task.find_one_and_update(
                {"_id": {"$nin": executing_list}, "done": False, "executor": executor},
                {"$set": {"executor": None, "status": TASK_STATUS["RETRYING"]}}
            )
            if not task:
                break
            transform_id(task)
            self.logger.warning(
                "Task %s should be executed by executor %s but not reported. Delete it." % (task["id"], executor)
            )
            delete_list.append(generate(task, True))

        # While there is still vacant position in the executor
        while vacant:
            # Find task undone task with no executor and assign it to the executor
            task = self.mongodb_task.find_one_and_update(
                {"done": False, "executor": None},
                {"$set": {"executor": executor, "report_time": datetime.datetime.now()}},
                return_document=pymongo.ReturnDocument.AFTER
            )
            if not task:
                self.logger.info("No more task to assign for executor %s." % executor)
                break
            transform_id(task)
            assign_list.append(generate(task))
            vacant = vacant - 1
            self.logger.info("Task %s assigned to executor %s." % (task, executor))

        return ReportReturn(ReturnCode.OK, delete_list, assign_list)

    def executors(self):
        """
        Interface: Executors
        Get a list of all executors
        :return: The list of all executors
        """
        self.logger.debug("Received RPC request: Executors.")

        # Find all executors and reformat the response.
        result = self.mongodb_executor.find()
        result = [x for x in result]
        executors = [
            Executor(str(x["_id"]), x["hostname"], x["report_time"].isoformat()) for x in result
        ]
        return ExecutorsReturn(ReturnCode.OK, executors)

if __name__ == "__main__":
    # Load configuration
    with open("config/main.json", "r") as f:
        config = json.load(f)
    retry_times = config["retry"]["times"]
    retry_interval = config["retry"]["interval"]

    # Generate a logger
    if "log" in config:
        logger = get_logger(
            "main",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("main", None, None)
    logger.info("Judicator main program started.")

    # Generate proxy for etcd and mongodb
    with open("config/etcd.json", "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)
    with open("config/mongodb.json", "r") as f:
        local_mongodb = generate_local_mongodb_proxy(json.load(f)["mongodb"], logger, True)
    # Get a connection to both task and executor collection in mongodb
    mongodb_task = local_mongodb.client[config["task"]["database"]][config["task"]["collection"]]
    mongodb_executor = local_mongodb.client[config["executor"]["database"]][config["executor"]["collection"]]

    # Create and start the register thread
    register_thread = threading.Thread(target=register)
    register_thread.setDaemon(True)
    register_thread.start()

    # Create and start the
    lead_thread = threading.Thread(target=lead)
    lead_thread.setDaemon(True)
    lead_thread.start()

    # Start the rpc server and serve until terminated
    server = TServer.TThreadedServer(
        Judicator.Processor(RPCService(logger, mongodb_task, mongodb_executor)),
        TSocket.TServerSocket(config["listen"]["address"], int(config["listen"]["port"])),
        TTransport.TBufferedTransportFactory(),
        TBinaryProtocol.TBinaryProtocolFactory()
    )
    try:
        logger.info("RPC server start to serve.")
        server.serve()
    except KeyboardInterrupt:
        logger.info("Received SIGINT.")
    except:
        logger.error("Accidentally terminated.", exc_info=True)
    logger.info("Exiting.")
