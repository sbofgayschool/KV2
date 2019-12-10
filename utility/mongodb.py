# -*- encoding: utf-8 -*-

__author__ = "chenty"

import pymongo
import pymongo.errors


def mongodb_generate_run_command(mongodb_config):
    return

class MongoDBProxy:
    def __init__(self, address, port, replica_name, log=None):
        self.address = address
        self.port = port
        self.replica_name = replica_name
        self.log = log
        self.client = pymongo.MongoClient(address, port)
        return

    def check_self_running(self):
        try:
            self.client.admin.command("replSetGetStatus")
            return True
        except pymongo.errors.OperationFailure as e:
            if e.code == 94:
                return True
            raise

    def initialize_replica_set(self, advertise_address, local_etcd, primary_key):
        local_etcd.set(
            primary_key,
            advertise_address,
            insert=True
        )
        primary = local_etcd.get(primary_key)
        if primary == advertise_address:
            self.client.admin.command({
                "replSetInitiate": {
                    "_id": self.replica_name,
                    "members": [{"_id": 0, "host": advertise_address}]
                }
            })
        else:
            client = pymongo.MongoClient(primary_key.split(":")[0], int(primary_key.split(":")[1]))
            conf = client.admin.command({"replSetGetConfig": 1})
            if not any([advertise_address == x["host"] for x in conf["config"]["members"]]):
                votes = sum([x.get("votes", 0) for x in conf["config"]["members"]])
                conf["config"]["members"].append({
                    "_id": max([x["_id"] for x in conf["config"]["members"]]) + 1,
                    "host": advertise_address,
                    "priority": 1 if votes < 7 else 0,
                    "votes": 1 if votes < 7 else 0
                })
                conf['config']['version'] += 1
                client.admin.command({'replSetReconfig': conf['config']})
        return

def generate_local_mongodb_proxy(mongodb_config):
    return MongoDBProxy("127.0.0.1", int(mongodb_config["listen"]["port"]), mongodb_config["replica_name"])