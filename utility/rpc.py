# -*- encoding: utf-8 -*-

__author__ = "chenty"

import datetime
import dateutil.parser

from rpc.judicator_rpc.ttypes import *


def extract(task, brief=False, compile=True, execute=True, result=True):
    res = {
        "id": task.id,
        "user": task.user,
        "done": task.done,
        "status": task.status,
        "executor": task.executor,
        "report_time": dateutil.parser.parse(task.report_time) if task.report_time else None
    }
    if brief:
        return res
    if compile and task.compile:
        res["compile"] = {
            "source": task.compile.source,
            "command": task.compile.command,
            "timeout": task.compile.timeout
        }
    else:
        res["compile"] = None
    if execute and task.execute:
        res["execute"] = {
            "source": task.execute.source,
            "command": task.execute.command,
            "timeout": task.execute.timeout,
            "standard": task.execute.standard
        }
    else:
        res["execute"] = None
    if result and task.result:
        res["result"] = {
            "compile": task.result.compile,
            "execute": task.result.execute,
        }
    else:
        res["result"] = None
    return res

def generate(task, brief=False, compile=True, execute=True, result=True):
    if isinstance(task["report_time"], str):
        t = task["report_time"]
    else:
        t = task["report_time"].isoformat()
    if brief:
        return TaskBrief(
            task["id"],
            task["user"],
            task["done"],
            task["status"],
            task["executor"],
            t
        )
    if compile and task["compile"]:
        c = Compile(task["compile"]["source"], task["compile"]["command"], task["compile"]["timeout"])
    else:
        c = None
    if execute and task["execute"]:
        e = Execute(
            task["execute"]["source"],
            task["execute"]["command"],
            task["execute"]["timeout"],
            task["execute"]["standard"]
        )
    else:
        e = None
    if result and task["result"]:
        r = Result(task["result"]["compile"], task["result"]["execute"])
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
