# -*- encoding: utf-8 -*-

__author__ = "chenty"

import pymongo
import pymongo.errors


def mongodb_generate_run_command(mongodb_config):
    """
    Generate run command for mongodb from config dictionary
    :param mongodb_config: mongodb config dictionary
    :return: A list of string representing the running command
    """
    # Return fundamental args
    return [
        mongodb_config["exe"],
        "--replSet",
        mongodb_config["replica_set"],
        "--bind_ip",
        mongodb_config["listen"]["address"],
        "--port",
        mongodb_config["listen"]["port"],
        "--dbpath",
        mongodb_config["data_dir"]
    ]

class MongoDBProxy:
    """
    Class representing a mongodb proxy connected to a mongodb instance
    """
    def __init__(self, address, port, replica_name, logger):
        """

        :param address: The address of the mongodb instance
        :param port: The port
        :param replica_name: The name of the replica set of the mongodb instance
        :param logger: The logger
        """
        self.address = address
        self.port = port
        self.replica_name = replica_name
        self.logger = logger
        # Generate a pymongo client, which can be accessed by others
        self.client = pymongo.MongoClient(address, port)
        return

    def check_self_running(self):
        """
        Check if the instance in running
        :return: True if it is, or False
        """
        try:
            # Use get replica set status to check running status
            self.client.admin.command("replSetGetStatus")
            return True
        except pymongo.errors.OperationFailure as e:
            # If an error occur and the error code is 94, it means the instance is running in a stand alone mode
            # This is not counted as an error
            # Otherwise, throw the exception
            if e.code == 94:
                return True
            raise

    def initialize_replica_set(self, advertise_address, local_etcd, primary_key):
        """
        Initialize or join the replica set of the mongodb instance
        :param advertise_address: Advertise address of the mongodb instance
        :param local_etcd: Proxy of local etcd
        :param primary_key: Key used to store the primary node of mongodb replica set in the etcd
        :return:
        """
        # Try to become leader of a new replica set by inserting its own advertise address to etcd
        # This can only happen when a new replica set is build and the key-value pair in etcd is empty
        try:
            local_etcd.set(
                primary_key,
                advertise_address,
                insert=True
            )
        except:
            self.logger.warn("Failed to insert %s." % primary_key, exc_info=True)

        # Check the current primary node of the replica set
        primary = local_etcd.get(primary_key)
        # If it is, then initialize the replica set
        # Else, join the replica set
        if primary == advertise_address:
            # Initialize the set
            self.client.admin.command({
                "replSetInitiate": {
                    "_id": self.replica_name,
                    "members": [{"_id": 0, "host": advertise_address}]
                }
            })
        else:
            # Create a client connected to the current primary node of mongodb replica set
            client = pymongo.MongoClient(primary.split(":")[0], int(primary.split(":")[1]))

            # Get the config
            conf = client.admin.command({"replSetGetConfig": 1})
            # If the instance is already inside the replica set, do nothing
            # This can happen when a instance is down unexpectedly and then reboot
            # Else, add it to the set
            if not any([advertise_address == x["host"] for x in conf["config"]["members"]]):
                # Check the amount ot voting members in the replica set
                votes = sum([x.get("votes", 0) for x in conf["config"]["members"]])
                # If the amount >= 7, this newly added instance will not be voter
                # Else, it will be voter
                # Add all needed information to the members config and update its version
                conf["config"]["members"].append({
                    "_id": max([x["_id"] for x in conf["config"]["members"]]) + 1,
                    "host": advertise_address,
                    "priority": 1 if votes < 7 else 0,
                    "votes": 1 if votes < 7 else 0
                })
                conf['config']['version'] += 1
                # Reconfig the replica set
                client.admin.command({'replSetReconfig': conf['config']})
        return

    def check_primary(self):
        """
        Check if current instance is primary of the replica set
        :return: True if it is, or False
        """
        # Done by executing the isMaster command
        return self.client.admin.command("isMaster")["isMaster"]

def generate_local_mongodb_proxy(mongodb_config, logger):
    """
    Generate a mongodb proxy instance from mongodb configuration
    :param mongodb_config: The configuration
    :param logger: The logger
    :return: Instance of mongodb proxy class
    """
    return MongoDBProxy(
        "127.0.0.1",
        int(mongodb_config["listen"]["port"]),
        mongodb_config["replica_set"],
        logger
    )

def transform_id(f):
    """
    Transform the _id (ObjectId) field to a id field (String) inside a json
    :param f: The json object
    :return: None
    """
    f["id"] = str(f["_id"])
    del f["_id"]
    return