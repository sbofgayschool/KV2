# -*- encoding: utf-8 -*-

__author__ = "chenty"

import urllib.parse
import requests
import json


def etcd_generate_run_command(etcd_config):
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
    if "proxy" in etcd_config:
        command.append("--proxy")
        command.append(etcd_config["proxy"])
    if "cluster" in etcd_config:
        if etcd_config["cluster"]["type"] == "init":
            if "discovery" in etcd_config["cluster"]:
                command.append("--discovery")
                command.append(etcd_config["cluster"]["discovery"])
            else:
                command.append("--initial-cluster-state")
                command.append("new")
                command.append("--initial-cluster")
                if "member" in etcd_config["cluster"]:
                    command.append(etcd_config["cluster"]["member"])
                else:
                    command.append(
                        etcd_config["name"] + "=" + \
                        "http://" + etcd_config["advertise"]["address"] + ":" + etcd_config["advertise"]["peer_port"]
                    )
        elif etcd_config["cluster"]["type"] == "join":
            command.append("--initial-cluster-state")
            command.append("existing")
            command.append("--initial-cluster")
            command.append(etcd_config["cluster"]["member"])
    return command

class EtcdProxy:
    def __init__(self, url, log=None):
        self.url = url
        self.log = log
        return

    def get_self_status(self):
        resp = requests.get(urllib.parse.urljoin(self.url, "/v2/stats/self"))
        if resp.status_code != 200:
            raise Exception("Get self status resulted in %d, not 200." % resp.status_code)
        return json.loads(resp.text)

    def add_and_get_members(self, peer_client):
        ret_code = requests.post(self.url, json={"peerURLs":[peer_client]}).status_code
        if ret_code != 200:
            raise Exception("Add member resulted in %d, not 200." % ret_code)
        resp = requests.get(urllib.parse.urljoin(self.url, "/v2/members"))
        if resp.status_code != 200:
            raise Exception("Get member resulted in %d, not 200." % resp.status_code)
        return dict((x["name"], x["peerURLs"][0]) for x in json.loads(resp.text)["member"])

    def set(self, key, value, ttl=None, insert=False, prev_value=False):
        url_postfix = urllib.parse.urljoin("/v2/keys", key)
        args = {"value": value}
        if ttl is not None:
            args["ttl"] = "" if ttl == 0 else int(ttl)
        if insert:
            args["prevExist"] = "true"
        if prev_value:
            args["prevValue"] = prev_value
        resp = requests.put(urllib.parse.urljoin(self.url, url_postfix), params=args)
        if resp.status_code != 200:
            raise Exception("Set key-value: %s-%s resulted in %d, not 200." % (key, value, resp.status_code))
        return json.loads(resp.text)

    def delete(self, key):
        url_postfix = urllib.parse.urljoin("/v2/keys", key)
        resp = requests.delete(urllib.parse.urljoin(self.url, url_postfix))
        if resp.status_code != 200:
            raise Exception("Set key: %s resulted in %d, not 200." % (key, resp.status_code))
        return json.loads(resp.text)

    def get(self, key, simple=True, none_if_empty=True):
        url_postfix = urllib.parse.urljoin("/v2/keys", key)
        resp = requests.delete(urllib.parse.urljoin(self.url, url_postfix))
        if resp.status_code == 404 and none_if_empty:
            return None
        elif resp.status_code != 200:
            raise Exception("Get key: %s resulted in %d, not 200." % (key, resp.status_code))
        res = json.loads(resp.text)
        if not simple:
            return res
        if res["node"].get("dir", False):
            return dict([(x["key"], x["value"]) for x in res["node"]["nodes"] if "value" in x])
        return res["node"]["value"]

def generate_local_etcd_proxy(etcd_config):
    return EtcdProxy("http://127.0.0.1:" + etcd_config["listen"]["client_port"])
