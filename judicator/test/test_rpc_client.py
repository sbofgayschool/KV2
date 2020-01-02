# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
os.environ["PYTHONPATH"] += ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())

import datetime
import zlib

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
        "add_time": None,
        "done": False,
        "status": 0,
        "executor": None,
        "report_time": None,
        "result": None
    }
    res = client.add(generate(data))
    print(res.result)
    print(res.id)
    print("=============\n")
    """

    """
    print("==== CANCEL ====")
    res = client.cancel("5e0897a0c17b388b35f2f310")
    print(res)
    print("================\n")
    """

    """
    print("==== GET ====")
    res = client.get("5e08f35dd6c57a942b9c2a31")
    print(res.result)
    print(extract(res.task))
    print(extract(res.task, brief=True))
    print("=============\n")
    """

    """
    print("==== SEARCH ====")
    res = client.search(None, 1, None, None, True, 2, 0)
    print(res.result)
    print(res.pages)
    for x in res.tasks:
        print(extract(x, brief=True))
    print("================\n")
    """

    """
    print("==== ADD: REAL ====")
    data = {
        "id": None,
        "user": 1,
        "compile": {
            "source": b"",
            # "command": b'x\x9c\xcb)V\xd0M\xcc\x01\x00\x07\x02\x01\xfa',
            # "command": b'x\x9c+\xceIM-P0\xe5JM\xce\xc8WP\xb7\xb7\xb7W\x07\x007\xd0\x05C',
            "command": b'x\x9c+\xceIM-P0\xe2JM\xce\xc8WP\xb7\xb7\xb7W\x07\x007\xac\x05@',
            "timeout": 3
        },
        "execute": {
            "input": b'x\x9c\x03\x00\x00\x00\x00\x01',
            "data": b"",
            "command": b'x\x9cKM\xce\xc8WPO,NIS\x07\x00\x16\xfa\x03\xac',
            "timeout": 3,
            "standard": b""
        },
        "add_time": None,
        "done": False,
        "status": 0,
        "executor": None,
        "report_time": datetime.datetime.now(),
        "result": None
    }
    res = client.add(generate(data))
    print(res.result)
    print(res.id)
    print("===================\n")
    """

    """
    print("==== GET REAL ====")
    res = client.get("5e0c8830b88731cc928c0666")
    print(res.result)
    print(extract(res.task))
    print(extract(res.task, brief=True))
    print("==================\n")
    """

    # """
    for i in range(4):
        print("==== ADD: REAL ====")
        data = {
            "id": None,
            "user": 1,
            "compile": {
                "source": b"",
                "command": zlib.compress(b"sleep 8\necho '???'"),
                "timeout": 10
            },
            "execute": {
                "input": zlib.compress(b"input\n"),
                "data": b"",
                "command": zlib.compress(b"while IFS= read -r line; do\n  printf '%s\n' \"$line\"\ndone\necho 'done~'"),
                "timeout": 3,
                "standard": b""
            },
            "add_time": None,
            "done": False,
            "status": 0,
            "executor": None,
            "report_time": datetime.datetime.now(),
            "result": None
        }
        res = client.add(generate(data))
        print(res.result)
        print(res.id)
        print("===================\n")
    # """

    """
    print("==== GET REAL ====")
    res = client.get("5e0b4bae2dd620088752f83c")
    print(res.result)
    print(extract(res.task))
    print(extract(res.task, brief=True))
    print("==================\n")
    print("==== GET REAL ====")
    res = client.get("5e0b4bae2dd620088752f83d")
    print(res.result)
    print(extract(res.task))
    print(extract(res.task, brief=True))
    print("==================\n")
    print("==== GET REAL ====")
    res = client.get("5e0b4bae2dd620088752f83e")
    print(res.result)
    print(extract(res.task))
    print(extract(res.task, brief=True))
    print("==================\n")
    print("==== GET REAL ====")
    res = client.get("5e0b4bae2dd620088752f83f")
    print(res.result)
    print(extract(res.task))
    print(extract(res.task, brief=True))
    print("==================\n")
    """

    """
    print("==== GET EXECUTOR ====")
    res = client.executors()
    print(res.result)
    for e in res.executors:
        print(e.id, e.hostname, e.report_time)
    print("======================\n")
    """

    transport.close()
