# -*- encoding: utf-8 -*-

__author__ = "chenty"

import json
import datetime
import threading
import time
import urllib.parse
import dateutil
import pymongo
import pymongo.errors
from bson.objectid import ObjectId
import dateutil.parser
import socket
import os

from rpc.judicator_rpc import Judicator
from rpc.judicator_rpc.ttypes import *
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from utility.function import get_logger, try_with_times, transform_address
from utility.etcd.proxy import generate_local_etcd_proxy
from utility.mongodb.proxy import generate_local_mongodb_proxy
from utility.task import check_id, transform_id, TASK_STATUS
from utility.rpc import extract, generate


# Global bool indicating if the program is working
working = True

def register(config, local_etcd, local_mongodb, logger):
    """
    Target function for register thread
    Regularly register the rpc service address in etcd, and unregister before exiting
    :param config: Configuration dictionary
    :param local_etcd: Local etcd proxy
    :param local_mongodb: Local mongodb proxy
    :param logger: The logger
    :return: None
    """
    logger.info("Register thread started.")

    retry_times = config["retry"]["times"]
    retry_interval = config["retry"]["interval"]
    reg_key = urllib.parse.urljoin(config["register"]["etcd_path"], config["name"])
    reg_value = config["advertise"]["address"] + ":" + config["advertise"]["port"]

    while working:
        time.sleep(config["register"]["interval"])
        try:
            # Check the local mongodb is running
            if not local_mongodb.check(local=False):
                raise Exception("Failed to confirm local mongodb status.")
            # Register itself
            local_etcd.set(reg_key, reg_value, ttl=config["register"]["ttl"])
            logger.info("Updated judicator service on etcd.")
        except:
            logger.error("Failed to update judicator service on etcd.", exc_info=True)

    # Delete judicator when exiting
    try_with_times(
        retry_times,
        retry_interval,
        False,
        logger,
        "delete judicator from etcd",
        local_etcd.delete,
        reg_key,
        reg_value
    )
    logger.info("Deleted judicator registration from etcd.")
    logger.info("Register thread terminating.")
    return

def lead(config, local_etcd, local_mongodb, mongodb_task, mongodb_executor, logger):
    """
    Target function for lead thread
    Compete against others to be leader, and, if become the leader, do regular check of tasks and executors
    :param config: Configuration dictionary
    :param local_etcd: Local etcd proxy
    :param local_mongodb: Local mongodb proxy
    :param mongodb_task: Mongodb collection of tasks
    :param mongodb_executor: Mongodb collection of executors
    :param logger: The logger
    """
    logger.info("Lead thread started.")
    while True:
        time.sleep(config["lead"]["interval"])

        try:
            # Check the local mongodb is running
            if not local_mongodb.check(local=False):
                raise Exception("Failed to confirm local mongodb status.")
            # Try to become leader when there are no previous leader
            try:
                local_etcd.set(
                    config["lead"]["etcd_path"],
                    config["name"],
                    ttl=config["lead"]["ttl"],
                    insert=True
                )
                logger.info("Become leader as there is previous leader.")
            except:
                logger.warning("Detected previous leader.", exc_info=True)
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
                logger.info("Updated leader information as current leader.")
            except:
                logger.warning("Failed to become leader.", exc_info=True)
                success = False

            # If this is the leader, do regular check
            if success:
                logger.info("Checking tasks and executors as leader.")

                # Set all expired task to retrying and remove their executor
                expire_time = datetime.datetime.now() - datetime.timedelta(seconds=config["task"]["expiration"])
                while True:
                    res = mongodb_task.find_one_and_update(
                        {"done": False, "executor": {"$ne": None}, "report_time": {"$lt": expire_time}},
                        {"$set": {"executor": None, "status": TASK_STATUS["RETRYING"]}}
                    )
                    if not res:
                        break
                    logger.warning("Set status of expired task %s to retrying." % str(res["_id"]))

                # Remove all expired executor from the record
                # Currently this is only for monitor usage
                expire_time = datetime.datetime.now() - datetime.timedelta(seconds=config["executor"]["expiration"])
                while True:
                    res = mongodb_executor.find_one_and_delete({"report_time": {"$lt": expire_time}})
                    if not res:
                        break
                    logger.warning("Deleted expired executor %s." % res["hostname"])

                logger.info("Checked tasks and executors.")
        except:
            logger.error("Failed to carry out leader process.", exc_info=True)

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
        self.logger.debug("Received rpc request: ping.")
        return ReturnCode.OK

    def add(self, task):
        """
        Interface: Add
        Add a new task
        :param task: Task struture, the task needed to be added
        :return: An AddResult structure containing the result and the generated id of the new task
        """
        self.logger.debug("Received rpc request: add.")

        # Extract and clean the task
        # The task is assumed to be valid if no error occurs during extraction
        try:
            task = extract(task, result=False)
        except:
            self.logger.error("Failed to extract new task.", exc_info=True)
            return AddReturn(ReturnCode.INVALID_INPUT, None)
        del task["id"]
        task["add_time"] = datetime.datetime.now()
        task["done"] = False
        task["status"] = TASK_STATUS["PENDING"]
        task["report_time"] = datetime.datetime.now()
        self.logger.info("Adding new task to database.")

        # Add and return the auto generated id
        try:
            result = self.mongodb_task.insert_one(task)
            self.logger.info("Added task %s.", str(result.inserted_id))
            return AddReturn(ReturnCode.OK, str(result.inserted_id))
        except pymongo.errors.WriteError as e:
            if "large" in str(e):
                self.logger.error("Failed to add new task as it is too large.", exc_info=True)
                return AddReturn(ReturnCode.TOO_LARGE, None)
            raise e
        except pymongo.errors.DocumentTooLarge:
            self.logger.error("Failed to add new task as it is too large.", exc_info=True)
            return AddReturn(ReturnCode.TOO_LARGE, None)
        except:
            self.logger.error("Failed to add new task.", exc_info=True)
            return AddReturn(ReturnCode.ERROR, None)

    def cancel(self, id):
        """
        Interface: Cancel
        Cancel a Task which has not been done
        :param id: The id of the job neede to be cancelled
        :return: Whether the cancellation is successful
        """
        self.logger.debug("Received rpc request: cancel.")
        # Input check
        if not check_id(id):
            return ReturnCode.INVALID_INPUT
        self.logger.info("Cancelling task %s." % id)

        # Try to update the status and executor of a undone task
        result = self.mongodb_task.find_one_and_update(
            {"_id": ObjectId(id), "done": False},
            {"$set": {"executor": None, "status": TASK_STATUS["CANCELLED"], "done": True}}
        )
        if result:
            self.logger.info("Cancelled task %s." % id)
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
        self.logger.debug("Received rpc request: search.")

        # Check and add conditions to the filter
        filter = {}
        try:
            if id:
                if not check_id(id):
                    raise Exception("Invalid id.")
                filter["_id"] = ObjectId(id)
            if user is not None:
                filter["user"] = user
            if start_time or end_time:
                filter["add_time"] = {}
                if start_time:
                    filter["add_time"]["$gte"] = dateutil.parser.parse(start_time)
                if end_time:
                    filter["add_time"]["$lte"] = dateutil.parser.parse(end_time)
        except:
            self.logger.error("Failed because of invalid data.", exc_info=True)
            return SearchReturn(ReturnCode.INVALID_INPUT, 0, [])
        self.logger.info("Searching with filter: %s." % str(filter))

        # Count result first for page calculation later
        cnt = self.mongodb_task.count(filter=filter)
        # If nothing found, return directly
        if cnt == 0:
            self.logger.info("Found empty result.")
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
        self.logger.info("Found result: %s." % str([x["id"] for x in result]))
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
        self.logger.debug("Received rpc request: get.")
        # Input check
        if not check_id(id):
            return ReturnCode.INVALID_INPUT
        self.logger.info("Getting task %s." % id)

        # Find and transform the result
        result = self.mongodb_task.find_one({"_id": ObjectId(id)})
        self.logger.info("Got task: %s." % id)
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
        self.logger.debug("Received rpc request: report.")
        # Input check
        if not (isinstance(executor, str) and executor and
                isinstance(complete, list) and
                isinstance(executing, list) and
                isinstance(vacant, int) and vacant >= 0):
            return ReportReturn(ReturnCode.INVALID_INPUT, [], [])
        self.logger.info("Received report from executor %s." % executor)

        # Refresh or add the information of the executor
        result = self.mongodb_executor.find_one_and_update(
            {"hostname": executor},
            {"$set": {"report_time": datetime.datetime.now()}}
        )
        if not result:
            self.mongodb_executor.insert_one({"hostname": executor, "report_time": datetime.datetime.now()})
        self.logger.info("Updated executor %s." % executor)

        delete_list, assign_list = [], []
        executing_list = []
        # Update all completed tasks, if the task indeed belong to the executor, and request the executor to delete it
        for t in complete:
            try:
                task = extract(t)
                self.logger.info("Updating complete task %s." % task["id"])
                result = False
                try:
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
                except pymongo.errors.OperationFailure as e:
                    # If the reported task is too big (this should not happened), set the status to error
                    if "large" in str(e):
                        self.logger.error("Failed to update task %s as it is too large." % task["id"], exc_info=True)
                        result = self.mongodb_task.find_one_and_update(
                            {"_id": ObjectId(task["id"]), "executor": executor},
                            {
                                "$set": {
                                    "done": True,
                                    "status": TASK_STATUS["UNKNOWN_ERROR"],
                                    "executor": None,
                                    "report_time": datetime.datetime.now(),
                                    "result": None
                                }
                            }
                        )
                    else:
                        raise e
                except pymongo.errors.DocumentTooLarge:
                    self.logger.error("Failed to update task %s as it is too large." % task["id"], exc_info=True)
                    result = self.mongodb_task.find_one_and_update(
                        {"_id": ObjectId(task["id"]), "executor": executor},
                        {
                            "$set": {
                                "done": True,
                                "status": TASK_STATUS["UNKNOWN_ERROR"],
                                "executor": None,
                                "report_time": datetime.datetime.now(),
                                "result": None
                            }
                        }
                    )
                except:
                    self.logger.error("Failed to update task %s." % task["id"], exc_info=True)
                if not result:
                    self.logger.warning("Skipped task %s as it is not found." % task["id"])
                else:
                    self.logger.info("Updated complete task %s." % task["id"])
                # Complete task is going to be deleted, no matter whether there is such a task record
                delete_list.append(generate(task, brief=True))
            except:
                # If errors occur during updating, the report_time should not be updated
                # and the task is going to cancelled (due to expiration) if it fails to be updated for several times
                self.logger.error("Failed to update complete task.", exc_info=True)
                continue

        # Update all executing tasks, and request the executor to delete it if the task does not belong to it
        for t in executing:
            try:
                task = extract(t, brief=True)
                self.logger.info("Updating executing task %s." % task["id"])
                # Put the id of the task to executing_list for unreported task check up
                executing_list.append(ObjectId(task["id"]))
                result = self.mongodb_task.find_one_and_update(
                    {"_id": ObjectId(task["id"]), "executor": executor},
                    {"$set": {"status": task["status"], "report_time": datetime.datetime.now()}}
                )
                if not result:
                    delete_list.append(generate(task, brief=True))
                    self.logger.warning("Skipping executing task %s as it is not found." % task["id"])
                else:
                    self.logger.info("Updated executing task %s." % task["id"])
            except:
                # The same thing when handling complete task failure
                self.logger.error("Failed to update executing task.", exc_info=True)

        # Find all tasks which should be executed by this executor but not appear in executing list
        # And set their status to retry, and also add them to delete list
        self.logger.info("Checking for unreported tasks.")
        while True:
            task = self.mongodb_task.find_one_and_update(
                {"_id": {"$nin": executing_list}, "done": False, "executor": executor},
                {"$set": {"executor": None, "status": TASK_STATUS["RETRYING"]}}
            )
            if not task:
                break
            transform_id(task)
            self.logger.warning(
                "Task %s should be executed by executor %s but not reported." % (task["id"], executor)
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
            self.logger.info("Assigned Task %s to executor %s." % (task["id"], executor))

        return ReportReturn(ReturnCode.OK, delete_list, assign_list)

    def executors(self):
        """
        Interface: Executors
        Get a list of all executors
        :return: The list of all executors
        """
        self.logger.debug("Received rpc request: executors.")

        # Find all executors and reformat the response.
        result = self.mongodb_executor.find()
        result = [x for x in result]
        executors = [
            Executor(str(x["_id"]), x["hostname"], x["report_time"].isoformat()) for x in result
        ]
        return ExecutorsReturn(ReturnCode.OK, executors)

def run(
    module_name="Judicator",
    etcd_conf_path="config/etcd.json",
    mongodb_conf_path="config/mongodb.json",
    main_conf_path="config/main.json"
):
    """
    Load config and run judicator main program
    :param module_name: Name of the caller module
    :param etcd_conf_path: Path to etcd config file
    :param mongodb_conf_path: Path to mongodb config file
    :param main_conf_path: Path to main config file
    :return: None
    """
    global working

    # Load configuration
    with open(main_conf_path, "r") as f:
        config = json.load(f)

    # Generate logger
    if "log" in config:
        logger = get_logger("main", config["log"]["info"], config["log"]["error"])
    else:
        logger = get_logger("main", None, None)
    logger.info("%s main program started." % module_name)

    # Generate proxy for etcd and mongodb
    with open(etcd_conf_path, "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)
    with open(mongodb_conf_path, "r") as f:
        local_mongodb = generate_local_mongodb_proxy(json.load(f)["mongodb"], local_etcd, logger)
    # Get a connection to both task and executor collection in mongodb
    mongodb_task = local_mongodb.client[config["task"]["database"]][config["task"]["collection"]]
    mongodb_executor = local_mongodb.client[config["executor"]["database"]][config["executor"]["collection"]]

    # Create and start the register thread
    register_thread = threading.Thread(target=register, args=(config, local_etcd, local_mongodb, logger))
    register_thread.setDaemon(True)
    register_thread.start()

    # Create and start the
    lead_thread = threading.Thread(
        target=lead,
        args=(config, local_etcd, local_mongodb, mongodb_task, mongodb_executor, logger)
    )
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
        logger.info("Starting rpc server.")
        server.serve()
    except KeyboardInterrupt:
        logger.info("Received SIGINT. Cancelling judicator registration on etcd.")
        # Wait for the register thread to delete registration and then stop
        working = False
        register_thread.join()
    except:
        logger.error("Accidentally terminated.", exc_info=True)

    logger.info("%s main program exiting." % module_name)
    return

def command_parser(parser):
    """
    Add judicator main args to args parser
    :param parser: The args parser
    :return: Callback function to modify config
    """
    # Add needed args
    parser.add_argument("--main-name", dest="main_name", default=None,
                        help="Name of the judicator")
    parser.add_argument("--main-listen-address", dest="main_listen_address", default=None,
                        help="Listen address of judicator rpc service")
    parser.add_argument("--main-listen-port", type=int, dest="main_listen_port", default=None,
                        help="Listen port of judicator rpc service")
    parser.add_argument("--main-advertise-address", dest="main_advertise_address", default=None,
                        help="Advertise address of judicator rpc service")
    parser.add_argument("--main-advertise-port", dest="main_advertise_port", default=None,
                        help="Advertise port of judicator rpc service")
    parser.add_argument("--main-print-log", dest="main_print_log", action="store_const", const=True, default=False,
                        help="Print the log of main module to stdout")

    def conf_generator(args, config_sub, client, services, start_order):
        """
        Callback function to modify judicator main configuration according to parsed args
        :param args: Parse args
        :param config_sub: Template config
        :param client: Docker client
        :param services: Dictionary of services
        :param start_order: List of services in starting order
        :return: None
        """
        # Modify config by parsed args
        if args.retry_times is not None:
            config_sub["retry"]["times"] = args.retry_times
        if args.retry_interval is not None:
            config_sub["retry"]["interval"] = args.retry_interval
        if args.main_name is not None:
            if args.main_name == "ENV":
                config_sub["name"] = os.environ.get("NAME")
            else:
                config_sub["name"] = args.main_name
        if args.main_listen_address is not None:
            config_sub["listen"]["address"] = transform_address(args.main_listen_address, client)
        if args.main_listen_port is not None:
            config_sub["listen"]["port"] = str(args.main_listen_port)
            config_sub["advertise"]["port"] = str(args.main_listen_port)
        if args.main_advertise_address is not None:
            config_sub["advertise"]["address"] = transform_address(args.main_advertise_address, client)
        if args.main_advertise_port is not None:
            if args.main_advertise_port == "DOCKER":
                config_sub["advertise"]["port"] = str(
                    client.port(socket.gethostname(), int(config_sub["listen"]["port"]))[0]["HostPort"]
                )
            else:
                config_sub["advertise"]["port"] = str(args.main_advertise_port)
        if args.main_print_log:
            config_sub.pop("log", None)
        if args.docker_sock is not None:
            if args.main_name is None:
                config_sub["name"] = socket.gethostname()

        # Generate information for execution
        services["main"] = {
            "pid_file": config_sub["pid_file"],
            "command": config_sub["exe"],
            "process": None
        }
        start_order.append("main")
        return

    return conf_generator

if __name__ == "__main__":
    run()
