# -*- encoding: utf-8 -*-

__author__ = "chenty"

import urllib.parse

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
    def __init__(self, address, port, replica_name, name, advertise_address, local_etcd, logger):
        """
        Initializer of the class
        :param address: The address of the mongodb instance
        :param port: The port
        :param replica_name: The name of the replica set of the mongodb instance
        :param name: Name of the mongodb, for registration usage
        :param advertise_address: The advertise address of the mongodb instance
        :param local_etcd: Local etcd instance
        :param logger: The logger
        """
        self.address = address
        self.port = port
        self.replica_name = replica_name
        self.name = name
        self.advertise_address = advertise_address
        self.local_etcd = local_etcd
        self.logger = logger
        # Generate a mongodb client, which can be accessed by others
        self.client = pymongo.MongoClient(self.address, self.port, replicaSet=replica_name)
        self.local_client = pymongo.MongoClient(self.address, self.port)
        return

    def check(self, local=True):
        """
        Check if the instance in running
        :param local: If only check the local one instead of the whole replica set
        :return: True if it is, or False
        """
        client = self.local_client if local else self.client
        try:
            # Check the status with command isMaster
            client.admin.command("isMaster")
            return True
        except:
            self.logger.error("Failed to check running status of mongodb.", exc_info=True)
            return False

    def initialize(self, init_key, reg_path):
        """
        Initialize or join the replica set of the mongodb instance
        :param init_key: Key for initializing replica set on etcd
        :param reg_path: Path for registration on etcd
        :return:
        """
        # Try to initialize a new replica set by inserting its own advertise address to init_key on etcd
        # This can only happen when a new replica set is build and the key-value pair in etcd is empty
        try:
            self.local_etcd.set(init_key, self.advertise_address, insert=True)
            # Initialize the set
            self.local_client.admin.command(
                "replSetInitiate", {
                    "_id": self.replica_name,
                    "members": [{"_id": 0, "host": self.advertise_address}]
                }
            )
            self.logger.info("Initialized replica set.")
        except:
            self.logger.warning("Failed to become the node to initialize the replica set.", exc_info=True)
        # Register on etcd.
        reg_key = urllib.parse.urljoin(reg_path, self.name)
        self.local_etcd.set(reg_key, self.advertise_address)
        self.logger.info("Registered self at %s on etcd." % reg_key)
        return

    def is_primary(self):
        """
        Get the primary node of the replica set
        :return: Address of the primary node
        """
        # Done by executing the isMaster command
        return self.local_client.admin.command("isMaster").get("ismaster", False)

    def adjust_replica_set(self, registered_member):
        """
        Adjust the replica set, including deleting member, adding member and adjusting voting
        :param registered_member: Set of registered member
        :return: None
        """
        conf = self.local_client.admin.command("replSetGetConfig", 1)
        member_status = dict(
            [(x["name"], x) for x in self.local_client.admin.command("replSetGetStatus", 1)["members"]]
        )
        max_id = max([x["_id"] for x in conf["config"]["members"]]) + 1

        # Delete all members which are not registered
        new_config = list(filter(lambda x: x["host"] in registered_member, conf["config"]["members"]))
        changed = len(new_config) != len(conf["config"]["members"])
        conf["config"]["members"] = new_config
        # Counting voting nodes
        votes = sum([x.get("votes", 0) for x in conf["config"]["members"]])
        # Adjust voting and priority
        for x in conf["config"]["members"]:
            if votes < 7 and member_status[x["host"]]["stateStr"] in ("SECONDARY", "PRIMARY") and x["votes"] == 0:
                x["votes"] = x["priority"] = 1
                votes += 1
                changed = True

        # Add all registered member to the replica set
        for x in registered_member:
            if x not in member_status:
                conf["config"]["members"].append({"_id": max_id, "host": x, "priority": 0, "votes": 0})
                max_id += 1
                changed = True

        # Applied changes if something has been changed
        if changed:
            self.logger.info("Adjusting the replica set with following members.")
            for x in conf["config"]["members"]:
                self.logger.info("%s", str(x))
            conf["config"]["version"] += 1
            force = not self.is_primary()
            self.logger.debug("Result of isMaster: %s." % str(self.local_client.admin.command("isMaster")))
            self.logger.debug("If in force mode: %s." % str(force))
            if force:
                self.logger.warning("Current node is not primary, using the force mode.")
            self.local_client.admin.command("replSetReconfig", conf["config"], force=force)
        else:
            self.logger.info("No changes applied to the replica set during adjusting.")
        return

    def shutdown_and_close(self):
        """
        Shutdown the local mongodb and close all connection
        :return: If the local mongodb has been shutdown
        """
        # Close replica client connection
        self.client.close()
        # Try to shutdown
        # An auto reconnect error indicates that the instance maybe shutdown correctly
        res = True
        try:
            self.local_client.admin.command("shutdown", 1)
        except pymongo.errors.AutoReconnect:
            self.logger.info("Possibly shutdown local mongodb.", exc_info=True)
        except:
            self.logger.error("Failed to shutdown mongodb.", exc_info=True)
            res = False
        # Close local connection
        # No need to close local connection
        # self.local_client.close()
        return res

    def cancel_registration(self, reg_path):
        """
        Cancel registration by deleting reg_key on etcd
        :param reg_path: Path for registration on etcd
        :return: None
        """
        # Delete it
        reg_key = urllib.parse.urljoin(reg_path, self.name)
        self.local_etcd.delete(reg_key, self.advertise_address, True)
        return

def generate_local_mongodb_proxy(config, local_etcd, logger):
    """
    Generate a mongodb proxy instance from mongodb configuration
    :param config: The configuration
    :param local_etcd: Local etcd instance
    :param logger: The logger
    :return: Instance of mongodb proxy class
    """
    return MongoDBProxy(
        "localhost",
        int(config["listen"]["port"]),
        config["replica_set"],
        config["name"],
        config["advertise"]["address"] + ":" + config["advertise"]["port"],
        local_etcd,
        logger
    )
