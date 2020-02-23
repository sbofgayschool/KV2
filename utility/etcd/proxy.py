# -*- encoding: utf-8 -*-

__author__ = "chenty"

import urllib.parse
import requests
import json


def etcd_generate_run_command(etcd_config):
    """
    Generate run command for etcd from config dictionary
    :param etcd_config: The config dictionary
    :return: A list of string representing the running command
    """
    # Fundamental args
    command = [
        etcd_config["exe"],
        "--name",
        etcd_config["name"],
        "--data-dir",
        etcd_config["data_dir"],
        "--listen-peer-urls",
        "http://" + etcd_config["listen"]["address"] + ":" + etcd_config["listen"]["peer_port"],
        "--listen-client-urls",
        "http://" + etcd_config["listen"]["address"] + ":" + etcd_config["listen"]["client_port"],
        "--initial-advertise-peer-urls",
        "http://" + etcd_config["advertise"]["address"] + ":" + etcd_config["advertise"]["peer_port"],
        "--advertise-client-urls",
        "http://" + etcd_config["advertise"]["address"] + ":" + etcd_config["advertise"]["client_port"],
    ]

    # If the instance should run as a proxy
    if "proxy" in etcd_config:
        command.append("--proxy")
        command.append(etcd_config["proxy"])
        command.append("--proxy-refresh-interval")
        command.append("10000")

    # If strict reconfig mode is on
    if etcd_config.get("strict_reconfig", False):
        command.append("--strict-reconfig-check")

    # If cluster information exists
    if "cluster" in etcd_config:
        # Two types are possible: init and join
        if etcd_config["cluster"]["type"] == "init":
            # When initializing, either discovery mode and token or peer members must be given
            if "discovery" in etcd_config["cluster"]:
                command.append("--discovery")
                command.append(etcd_config["cluster"]["discovery"])
            else:
                command.append("--initial-cluster-state")
                command.append("new")
                command.append("--initial-cluster")
                # If member argument is given, use it.
                # Otherwise, suppose that this instance is the only instance in the cluster
                if "member" in etcd_config["cluster"]:
                    command.append(etcd_config["cluster"]["member"])
                else:
                    command.append(
                        etcd_config["name"] + "=" + \
                        "http://" + etcd_config["advertise"]["address"] + ":" + etcd_config["advertise"]["peer_port"]
                    )

        elif etcd_config["cluster"]["type"] == "join":
            # When joining, list of cluster members must be given
            command.append("--initial-cluster-state")
            command.append("existing")
            command.append("--initial-cluster")
            command.append(etcd_config["cluster"]["member"])
    return command

class EtcdProxy:
    """
    Class for etcd proxy connected to a etcd instance
    All etcd operations should be passed through this proxy
    """
    def __init__(self, url, logger):
        """
        Initializer for the class
        :param url: Url of the etcd instance
        :param logger: Logger used by the proxy
        """
        self.url = url
        self.logger = logger
        return

    def get_self_status(self):
        """
        Get the status of the instance
        :return: Status of the instance
        """
        # Try to get the status by HTTP request and return the parsed json
        resp = requests.get(urllib.parse.urljoin(self.url, "/v2/stats/self"))
        if not resp:
            raise Exception("Get self status resulted in %d, not 200." % resp.status_code)
        return json.loads(resp.text)

    def add_and_get_members(self, name, peer_url, get=True):
        """
        Add a new member (if required) and then get members of the cluster from the instance
        :param name: Name of adding node
        :param peer_url: Peer url of the new member
        :param get: If only wish to get the members
        :return: Dictionary containing name and url of cluster members
        """
        # Get existing members first
        resp = requests.get(urllib.parse.urljoin(self.url, "/v2/members"))
        if not resp:
            raise Exception("Get existing member resulted in %d, not 200." % resp.status_code)

        # If current node already exists
        resp = json.loads(resp.text)["members"]
        self.logger.info("Got cluster member.")
        if get:
            return dict((x["name"], x["peerURLs"][0]) for x in resp)
        for x in resp:
            if x["name"] == name:
                self.logger.warning("Member %s is already in the cluster. Deleting and re-adding it." % name)
                self.remove_member(name, None)
                break

        # Try to add a member
        resp = requests.post(
            urllib.parse.urljoin(self.url, "/v2/members"),
            json={"peerURLs":[peer_url]}
        )
        if not resp:
            raise Exception("Add member resulted in %d, not 200." % resp.status_code)
        id = json.loads(resp.text)["id"]
        self.logger.info("Added member %s to the cluster." % name)

        # Get existing members after adding
        resp = requests.get(urllib.parse.urljoin(self.url, "/v2/members"))
        if not resp:
            raise Exception("Get member resulted in %d, not 200." % resp.status_code)

        # Extract and return exist members
        resp = json.loads(resp.text)["members"]
        for x in resp:
            if x["id"] == id:
                x["name"] = name
                break
        return dict((x["name"], x["peerURLs"][0]) for x in resp)

    def remove_member(self, name, peer_url):
        """
        Remove a member from etcd cluster
        :param name: Name of the member
        :param peer_url: Expected peer url of the member
        :return: None
        """
        # Get members and find id for self
        resp = requests.get(urllib.parse.urljoin(self.url, "/v2/members"))
        if not resp:
            raise Exception("Get member resulted in %d, not 200." % resp.status_code)

        # Extract search the result
        resp = json.loads(resp.text)["members"]
        # If more than one node exist, do the deletion
        # Otherwise, there is no need for deletion
        if len(resp) > 1:
            id = None
            for x in resp:
                if x["name"] == name and (peer_url is None or peer_url == x["peerURLs"][0]):
                    id = x["id"]
                    break
            # If the node is found, delete it
            # Otherwise, skip deletion
            if id:
                url_postfix = urllib.parse.urljoin("/v2/members/", str(id))
                resp = requests.delete(urllib.parse.urljoin(self.url, url_postfix))
                if not resp:
                    raise Exception("Delete member resulted in %d, not 200." % resp.status_code)
                self.logger.info("Deleted member %s." % name)
            else:
                self.logger.warning("Failed to get id of the node. Skipped deletion.")
        else:
            self.logger.info("Only one node in cluster. Skipped deletion.")
        return

    def set(self, key, value, ttl=None, insert=False, prev_value=None):
        """
        Set a key-value pair on etcd
        :param key: The key
        :param value: The value
        :param ttl: The ttl of the key
        :param insert: If the key should not exist
        :param prev_value: If the previous value of the key should equal to specified value
        :return: Loaded response
        """
        url_postfix = urllib.parse.urljoin("/v2/keys/", key)
        # Put body
        data = {"value": value}
        # Url arguments
        params = {}
        # Add necessary arguments to post body and/or url arguments
        if ttl is not None:
            data["ttl"] = "" if ttl == 0 else int(ttl)
        if insert:
            params["prevExist"] = "false"
        if prev_value is not None:
            data["prevExist"] = "true"
            data["prevValue"] = prev_value

        # Set the key-value pair
        resp = requests.put(urllib.parse.urljoin(self.url, url_postfix), params=params, data=data)
        if not resp:
            raise Exception("Set key: %s, value: %s resulted in %d, not 200." % (key, value, resp.status_code))

        return json.loads(resp.text)

    def delete(self, key, prev_value=None, skip_not_found=False):
        """
        Delete a key-value pair
        :param key: The key
        :param prev_value: Expected previous value
        :param skip_not_found: If return None when the key not exsits
        :return: Loaded response
        """
        url_postfix = urllib.parse.urljoin("/v2/keys/", key)

        # Delete the pair
        resp = requests.delete(
            urllib.parse.urljoin(self.url, url_postfix), params={} if prev_value is None else {"prevValue": prev_value}
        )
        if not resp:
            if resp.status_code == 404 and skip_not_found:
                return None
            raise Exception("Delete key: %s resulted in %d, not 200." % (key, resp.status_code))

        return json.loads(resp.text)

    def get(self, key, simple=True, none_if_empty=True):
        """
        Get a key-value pair or a dictionary
        :param key: The key
        :param simple: If should return in simple mode
        :param none_if_empty: If should return None when encounter a non-existing key
        :return:
        """
        url_postfix = urllib.parse.urljoin("/v2/keys/", key)

        # Get the value
        resp = requests.get(urllib.parse.urljoin(self.url, url_postfix))
        # When the key not exists, either return None or throw an exception
        if resp.status_code == 404 and none_if_empty:
            return None
        elif not resp:
            raise Exception("Get key: %s resulted in %d, not 200." % (key, resp.status_code))

        # Load the response
        res = json.loads(resp.text)
        # Return the response directly if not in a simple mode
        if not simple:
            return res
        # If in simple mode and the key is a dir
        # Return dictionary containing key-value pairs inside it, and no subdir information is included
        # Else, simply return the value of the key
        if res["node"].get("dir", False):
            return dict([(x["key"], x["value"]) for x in res["node"].get("nodes", []) if "value" in x])
        return res["node"]["value"]

def generate_local_etcd_proxy(etcd_config, logger):
    """
    Generate a etcd proxy instance from etcd configuration
    :param etcd_config: The etcd configuration
    :param logger: The logger
    :return: Instance of etcd proxy connected to the etcd instance
    """
    return EtcdProxy("http://localhost:" + etcd_config["listen"]["client_port"], logger)
