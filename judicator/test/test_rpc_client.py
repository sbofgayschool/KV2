# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
os.environ["PYTHONPATH"] += ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())

import datetime

from rpc.judicator_rpc import Judicator
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol

from utility.rpc import generate, extract


if __name__ == "__main__":
    transport = TTransport.TBufferedTransport(TSocket.TSocket("127.0.0.1", 4000))
    client = Judicator.Client(TBinaryProtocol.TBinaryProtocol(transport))

    transport.open()

    print("==== PING ====")
    print(client.ping())
    print("==============\n")

    """
    print("==== ADD ====")
    data = {
        "id": None,
        "user": 1,
        "compile": {
            "source": b"compile_source",
            "command": b"compile_command",
            "timeout": 1
        },
        "execute": {
            "input": b"execute_input",
            "data": b"execute_data",
            "command": b"execute_command",
            "timeout": 2,
            "standard": b"execute_standard"
        },
        "done": False,
        "status": 0,
        "executor": None,
        "report_time": datetime.datetime.now(),
        "result": None
    }
    res = client.add(generate(data))
    print(res.result)
    print(res.id)
    print("=============\n")

    print("==== CANCEL ====")
    res = client.cancel("5e0897a0c17b388b35f2f310")
    print(res)
    print("================\n")
    """

    print("==== GET ====")
    res = client.get("5e08f35dd6c57a942b9c2a31")
    print(res.result)
    print(extract(res.task))
    print(extract(res.task, brief=True))
    print("=============\n")

    """
    print("==== SEARCH ====")
    res = client.search(None, 1, datetime.datetime(2019, 12, 29, 12, 10, 8, 426000).isoformat(), None, True, 2)
    print(res.result)
    for x in res.tasks:
        print(extract(x, brief=True))
    print("================\n")
    """

    transport.close()