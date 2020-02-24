# -*- encoding: utf-8 -*-

__author__ = "chenty"

import dateutil.parser
import random

from rpc.judicator_rpc import Judicator
from rpc.judicator_rpc.ttypes import *
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol


def extract(task, brief=False, compile=True, execute=True, result=True):
    """
    Extract dictionary from rpc Task structure (class)
    :param task: The original structure
    :param brief: If the structure is a brief one (TaskBrief)
    :param compile: If compile information needs to be extracted
    :param execute: Same to compile, but execute information
    :param result: Same to compile, but result information
    :return: Extracted dictionary
    """
    # Fundamental fields
    # This is all TaskBrief structure contains
    # Time string is parsed into datetime object
    res = {
        "id": task.id,
        "user": task.user,
        "add_time": dateutil.parser.parse(task.add_time) if task.add_time else None,
        "done": task.done,
        "status": task.status,
        "executor": task.executor,
        "report_time": dateutil.parser.parse(task.report_time) if task.report_time else None
    }
    if brief:
        return res

    # Extract compile information
    if compile and task.compile:
        res["compile"] = {
            "source": task.compile.source,
            "command": task.compile.command,
            "timeout": task.compile.timeout
        }
    else:
        res["compile"] = None

    # Execute information
    if execute and task.execute:
        res["execute"] = {
            "input": task.execute.input,
            "data": task.execute.data,
            "command": task.execute.command,
            "timeout": task.execute.timeout,
            "standard": task.execute.standard
        }
    else:
        res["execute"] = None

    # Result information
    if result and task.result:
        res["result"] = {
            "compile_output": task.result.compile_output,
            "compile_error": task.result.compile_error,
            "execute_output": task.result.execute_output,
            "execute_error": task.result.execute_error,
        }
    else:
        res["result"] = None

    return res

def generate(task, brief=False, compile=True, execute=True, result=True):
    """
    Generate rpc Task structure (class) from a given dictionary
    :param task: The dictionary
    :param brief: If a TaskBrief structure should be generated
    :param compile: If compile information needs to be included
    :param execute: Same to compile, but execute information
    :param result: Same to compile, but result information
    :return: Generated Task structure
    """
    # The add_time must be converted into a string, if necessary
    if task["add_time"] is None or isinstance(task["add_time"], str):
        add_time = task["add_time"]
    else:
        add_time = task["add_time"].isoformat()

    # Same to the report_time
    if task["report_time"] is None or isinstance(task["report_time"], str):
        report_time = task["report_time"]
    else:
        report_time = task["report_time"].isoformat()

    # If BriefTask should be generated, just return fundamental fields
    if brief:
        return TaskBrief(
            task["id"],
            task["user"],
            add_time,
            task["done"],
            task["status"],
            task["executor"],
            report_time
        )

    # Generate compile information
    if compile and task["compile"]:
        c = Compile(
            task["compile"]["source"],
            task["compile"]["command"],
            task["compile"]["timeout"]
        )
    else:
        c = None

    # Execute information
    if execute and task["execute"]:
        e = Execute(
            task["execute"]["input"],
            task["execute"]["data"],
            task["execute"]["command"],
            task["execute"]["timeout"],
            task["execute"]["standard"]
        )
    else:
        e = None

    # Result information
    if result and task["result"]:
        r = Result(
            task["result"]["compile_output"],
            task["result"]["compile_error"],
            task["result"]["execute_output"],
            task["result"]["execute_error"]
        )
    else:
        r = None

    return Task(
            task["id"],
            task["user"],
            c,
            e,
            add_time,
            task["done"],
            task["status"],
            task["executor"],
            report_time,
            r
        )

def select_from_etcd_and_call(func, local_etcd, judicator_path, logger, *args, **kwargs):
    """
    Select a judicator from etcd and call rpc process.
    :param func: Name of the function
    :param local_etcd: Etcd proxy
    :param judicator_path: Path to judicator services on etcd
    :param logger: Logger object.
    :return: Return of the rpc call.
    """
    # Get all judicator rpc address and choose one randomly
    judicator = local_etcd.get(judicator_path)
    logger.info("Got judicator list %s." % str(judicator))
    if not judicator:
        raise Exception("No judicator rpc service detected.")
    name, address = random.choice(tuple(judicator.items()))
    host, port = address.split(":")
    logger.debug("Making %s call to judicator %s at %s" % (func, name, address))

    # Start rpc transport
    transport = TTransport.TBufferedTransport(TSocket.TSocket(host, int(port)))
    client = Judicator.Client(TBinaryProtocol.TBinaryProtocol(transport))
    transport.open()
    # Call and return
    res = client.__getattribute__(func)(*args, **kwargs)
    transport.close()

    return res
