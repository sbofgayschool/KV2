# -*- encoding: utf-8 -*-

__author__ = "chenty"

import dateutil.parser

from rpc.judicator_rpc.ttypes import *


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
    res = {
        "id": task.id,
        "user": task.user,
        "done": task.done,
        "status": task.status,
        "executor": task.executor,
        # Parse the time string to a datetime object
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
            "source": task.execute.source,
            "command": task.execute.command,
            "timeout": task.execute.timeout,
            "standard": task.execute.standard
        }
    else:
        res["execute"] = None

    # Result information
    if result and task.result:
        res["result"] = {
            "compile": task.result.compile,
            "execute": task.result.execute,
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
    # The report_time must be converted into a string, if necessary
    if isinstance(task["report_time"], str):
        t = task["report_time"]
    else:
        t = task["report_time"].isoformat()

    # If BriefTask should be generated, just return fundamental fields
    if brief:
        return TaskBrief(
            task["id"],
            task["user"],
            task["done"],
            task["status"],
            task["executor"],
            t
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
            task["execute"]["source"],
            task["execute"]["command"],
            task["execute"]["timeout"],
            task["execute"]["standard"]
        )
    else:
        e = None

    # Result information
    if result and task["result"]:
        r = Result(
            task["result"]["compile"],
            task["result"]["execute"]
        )
    else:
        r = None

    return Task(
            task["id"],
            task["user"],
            c,
            e,
            task["done"],
            task["status"],
            task["executor"],
            task["report_time"],
            r
        )
