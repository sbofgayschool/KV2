# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import flask

from utility.function import get_logger
from utility.etcd import generate_local_etcd_proxy
from utility.rpc import select_from_etcd_and_call


# Load configuration
with open("config/templates/uwsgi.json", "r") as f:
    config = json.load(f)

# Get the Flask object
server = flask.Flask(__name__)

# Generate a logger
if "log" in config:
    logger = get_logger(
        server.logger,
        config["log"]["info"],
        config["log"]["error"]
    )
else:
    logger = get_logger(server.logger, None, None)

# Generate proxy for etcd and mongodb
with open("config/etcd.json", "r") as f:
    local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)

@server.route("/test", methods=["GET"])
def test():
    return flask.make_response(
        "KV2 gateway server is working. Etcd path: %s." % config["server"]["judicator_etcd_path"]
    )

@server.route("/api/task", methods=["POST"])
def api_task_add():
    pass

@server.route("/api/task", methods=["DELETE"])
def api_task_cancel():
    pass

@server.route("/api/task/list", methods=["GET"])
def api_task_search():
    pass

@server.route("/api/task", methods=["GET"])
def api_task_get():
    pass

@server.route("/api/executors", methods=["GET"])
def api_executors():
    res = select_from_etcd_and_call("executors", local_etcd, config["server"]["judicator_etcd_path"], logger)
    return flask.jsonify({
        "result": res.result,
        "executors": [{"id": x.id, "hostname": x.hostname, "report_time": x.report_time} for x in res.executors]
    })

@server.route("/api/judicators", methods=["GET"])
def api_judicators():
    pass