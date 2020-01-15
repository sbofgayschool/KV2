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
    def __init__(self, address, port, replica_name, logger, replica):
        """
        Initializer of the class
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
        self.client = None
        self.in_replica = False
        self.reconnect(replica)

        return

    def reconnect(self, replica):
        """
        Reconnect the pymongo client to the address and host
        This can switch the internal client between single mode and replica mode
        :param replica: If the replica mode is on
        :return: None
        """
        if self.client:
            try:
                self.client.close()
            except:
                self.logger("Failed to close previous connection.", exc_info=True)
        if replica:
            self.client = pymongo.MongoClient(self.address, self.port, replicaSet=self.replica_name)
        else:
            self.client = pymongo.MongoClient(self.address, self.port)
        self.in_replica = replica
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

    def initialize_replica_set(self, advertise_address, reg_key, primary_key, local_etcd):
        """
        Initialize or join the replica set of the mongodb instance
        :param advertise_address: Advertise address of the mongodb instance
        :param reg_key: Key used for mongodb registration
        :param primary_key: Key used to store the primary node of mongodb replica set in the etcd
        :param local_etcd: Proxy of local etcd
        :return:
        """
        # Registration first
        local_etcd.set(
            reg_key,
            advertise_address
        )
        # Try to become leader of a new replica set by inserting its own advertise address to etcd
        # This can only happen when a new replica set is build and the key-value pair in etcd is empty
        try:
            local_etcd.set(
                primary_key,
                advertise_address,
                insert=True
            )
        except:
            self.logger.warning("Failed to insert %s." % primary_key, exc_info=True)

        # Check the current primary node of the replica set
        primary = local_etcd.get(primary_key)
        # If it is, then initialize the replica set
        # Else, join the replica set
        if primary == advertise_address:
            # Initialize the set
            self.client.admin.command(
                "replSetInitiate", {
                    "_id": self.replica_name,
                    "members": [{"_id": 0, "host": advertise_address}]
                }
            )
            self.logger.info("Replica set intialized.")
        else:
            # Create a client connected to the current primary node of mongodb replica set
            client = pymongo.MongoClient(primary.split(":")[0], int(primary.split(":")[1]))

            # Get the config
            conf = client.admin.command("replSetGetConfig", 1)
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
                conf["config"]["version"] += 1
                # Reconfig the replica set
                client.admin.command("replSetReconfig", conf["config"])
                self.logger.info("Added member %s to the replica set." % advertise_address)
            else:
                self.logger.warning("Member %s is alread in the replica set." % advertise_address)
        return

    def get_primary(self):
        """
        Get the primary node of the replica set
        :return: Address of the primary node
        """
        # Done by executing the isMaster command
        return self.client.admin.command("isMaster").get("primary", "")

    def remove_from_replica_set(self, advertise_address):
        """
        Remove a node from replica set
        :param advertise_address: The advertise address from the replica set
        :return: None
        """
        if not self.in_replica:
            return
        # Get the config
        conf = self.client.admin.command("replSetGetConfig", 1)
        # If more than one nodes exist in the replica set, find current node and delete it
        if len(conf["config"]["members"]) > 1:
            removed = False
            for i in range(len(conf["config"]["members"])):
                if conf["config"]["members"][i]["host"] == advertise_address:
                    # Deletion
                    del conf["config"]["members"][i]
                    conf["config"]["version"] += 1
                    # Force is added here to prevent some incomplete configure
                    # Warning: the parameter force actually should not be added here
                    self.client.admin.command("replSetReconfig", conf["config"], force=True)
                    removed = True
                    self.logger.info("Removed %s from replica set." % advertise_address)
                    break
            if not removed:
                self.logger.warning("Failed to find the node %s in replica set." % advertise_address)
        else:
            self.logger.warning("Skipped removing the only mongodb from the replica set.")
        return

def generate_local_mongodb_proxy(mongodb_config, logger, replica=False):
    """
    Generate a mongodb proxy instance from mongodb configuration
    :param mongodb_config: The configuration
    :param logger: The logger
    :param replica: If the replica mode is on
    :return: Instance of mongodb proxy class
    """
    return MongoDBProxy(
        "localhost",
        int(mongodb_config["listen"]["port"]),
        mongodb_config["replica_set"],
        logger,
        replica
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