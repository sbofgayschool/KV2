# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import flask
import zlib
import tempfile
from os.path import join
import zipfile

from rpc.judicator_rpc.ttypes import *

from utility.function import get_logger, check_task_dict_size, check_id
from utility.etcd import generate_local_etcd_proxy
from utility.rpc import select_from_etcd_and_call, extract, generate


# Load configuration
with open("config/templates/uwsgi.json", "r") as f:
    config = json.load(f)["server"]

# Get the Flask object
server = flask.Flask(__name__, template_folder=config["template"])
server.jinja_env.variable_start_string = '[['
server.jinja_env.variable_end_string = ']]'
server.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# Generate a logger
if "log" in config:
    logger = get_logger(
        server.logger,
        config["log"]["info"],
        config["log"]["error"]
    )
else:
    logger = get_logger(server.logger, None, None)
logger.info("Gateway server program started.")

# Generate proxy for etcd and mongodb
with open("config/etcd.json", "r") as f:
    local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)

@server.route("/api/test", methods=["GET"])
def api_test():
    """
    Flask Handler: API Interface: Test if the gateway is working
    :return:
    """
    return flask.make_response("Khala gateway server is working.")

@server.route("/api/task", methods=["POST"])
def api_task_add():
    """
    Flask Handler: API Interface: Add a new task
    :return: Json with result code and id of new task
    """
    # Extract all necessary data
    try:
        data = {
            "id": None,
            "user": int(flask.request.form.get("user")),
            "compile": {
                "source": b"",
                "command": zlib.compress(flask.request.form.get("compile_command").encode("utf-8")),
                "timeout": int(flask.request.form.get("compile_timeout"))
            },
            "execute": {
                "input": zlib.compress(flask.request.form.get("execute_input").encode("utf-8")),
                "data": b"",
                "command": zlib.compress(flask.request.form.get("execute_command").encode("utf-8")),
                "timeout": int(flask.request.form.get("execute_timeout")),
                "standard": zlib.compress(flask.request.form.get("execute_standard").encode("utf-8"))
            },
            "add_time": None,
            "done": False,
            "status": 0,
            "executor": None,
            "report_time": None,
            "result": None
        }
    except:
        logger.error("Failed to parse added task.", exc_info=True)
        return flask.jsonify({"result": ReturnCode.INVALID_INPUT, "id": None})

    logger.info("Generating all extra fields for added task.")
    # Deal with compile source
    compile_source = flask.request.files.get("compile_source")
    compile_source_str = flask.request.form.get("compile_source_str")
    compile_source_name = flask.request.form.get("compile_source_name")
    # If the zip file has been uploaded, use it
    # Else if some text is given, zipped it and use it
    if compile_source:
        logger.info("Detected compile source.")
        data["compile"]["source"] = compile_source.stream.read()
    elif compile_source_str and compile_source_name:
        logger.info("Detected compile source text.")
        # Create a temp dir
        temp_dir = tempfile.TemporaryDirectory(dir=config["data_dir"])
        # Write the text in the file with specified name
        file_path = join(temp_dir.name, compile_source_name)
        with open(file_path, "w") as f:
            f.write(compile_source_str)
        # Create the zip file
        zip_path = join(temp_dir.name, "source.zip")
        with zipfile.ZipFile(zip_path, "w") as f:
            f.write(file_path, compile_source_name)
        # Read the binary
        with open(zip_path, "rb") as f:
            data["compile"]["source"] = f.read()

    # Deal with execute data
    execute_data = flask.request.files.get("execute_data")
    execute_data_str = flask.request.form.get("execute_data_str")
    execute_data_name = flask.request.form.get("execute_data_name")
    # If the zip file has been uploaded, use it
    # Else if some text is given, zipped it and use it
    if execute_data:
        logger.info("Detected execute data.")
        data["execute"]["data"] = execute_data.stream.read()
    elif execute_data_str and execute_data_name:
        logger.info("Detected execute data text.")
        # Create a temp dir
        temp_dir = tempfile.TemporaryDirectory(dir=config["data_dir"])
        # Write the text in the file with specified name
        file_path = join(temp_dir.name, execute_data_name)
        with open(file_path, "w") as f:
            f.write(execute_data_str)
        # Create the zip file
        zip_path = join(temp_dir.name, "data.zip")
        with zipfile.ZipFile(zip_path, "w") as f:
            f.write(file_path, execute_data_name)
        # Read the binary
        with open(zip_path, "rb") as f:
            data["execute"]["data"] = f.read()

    logger.info("Generated all fields for added task.")

    # Check the size of the data before submit.
    if not check_task_dict_size(data):
        return flask.jsonify({"result": ReturnCode.TOO_LARGE, "id": None})

    # Add through rpc and return
    res = select_from_etcd_and_call("add", local_etcd, config["judicator_etcd_path"], logger, generate(data))
    return flask.jsonify({"result": res.result, "id": res.id})

@server.route("/api/task", methods=["DELETE"])
def api_task_cancel():
    """
    Flask Handler: API Interface: Cancel a task
    :return: Json with only result code
    """
    # Get the id, and return directly if no id is specified
    id = flask.request.args.get("id", None)
    if id is None:
        return flask.jsonify({"result": ReturnCode.INVALID_INPUT})

    # Cancel and return the result
    logger.info("Canceling task %s." % id)
    res = select_from_etcd_and_call("cancel", local_etcd, config["judicator_etcd_path"], logger, id)
    return flask.jsonify({"result": res})

@server.route("/api/task/list", methods=["GET"])
def api_task_search():
    """
    Flask Handler: API Interface: Search for tasks with specified conditions
    :return: Json containing the result, including total page number
    """
    # Check and get all conditions
    failed_result = {"result": ReturnCode.INVALID_INPUT, "pages": 0, "tasks": []}
    try:
        id = flask.request.args.get("id", None)
        if id is not None and not check_id(id):
            return flask.jsonify(failed_result)
        user = flask.request.args.get("user", None)
        if user is not None:
            user = int(user)
            if not 0 <= user:
                return flask.jsonify(failed_result)
        start_time = flask.request.args.get("start_time", None)
        end_time = flask.request.args.get("end_time", None)
        old_to_new = flask.request.args.get("old_to_new", None)
        if old_to_new is not None:
            old_to_new = True
        limit = int(flask.request.args.get("limit", 0))
        if not limit >= 0:
            return flask.jsonify(failed_result)
        page = int(flask.request.args.get("page", 0))
        if not page >= 0:
            return flask.jsonify(failed_result)
    except:
        logger.error("Failed to get all search conditions.", exc_info=True)
        return flask.jsonify(failed_result)

    logger.info("Parsed searching conditions.")

    # Search for the task
    res = select_from_etcd_and_call(
        "search",
        local_etcd,
        config["judicator_etcd_path"],
        logger,
        id,
        user,
        start_time,
        end_time,
        old_to_new,
        limit,
        page
    )

    # Handle the result and return
    tasks = [extract(x, brief=True) for x in res.tasks]
    logger.info("Found result: %s." % str([x["id"] for x in tasks]))
    for t in tasks:
        t["add_time"] = "" if not t["add_time"] else t["add_time"].isoformat()
        t["report_time"] = "" if not t["report_time"] else t["report_time"].isoformat()

    return flask.jsonify({"result": res.result, "pages": res.pages, "tasks": tasks})

@server.route("/api/task", methods=["GET"])
def api_task_get():
    """
    Flask Handler: API Interface: Get a specified task, or one of its files
    :return: A file if getting a file, or a json containing tasks
    """
    # Get the id and the name of the file
    id = flask.request.args.get("id", None)
    file = flask.request.args.get("file", None)
    # Return directly if no id is specified
    if id is None:
        return flask.jsonify({"result": ReturnCode.INVALID_INPUT, "task": None})

    # Get the task
    logger.info("Getting task %s." % id)
    res = select_from_etcd_and_call("get", local_etcd, config["judicator_etcd_path"], logger, id)
    # If not found, return
    # Otherwise return required data.
    if res.result != ReturnCode.OK:
        if file:
            flask.abort(404)
        return flask.jsonify({"result": ReturnCode.NOT_EXIST, "task": None})

    task = extract(res.task)

    # Decompress compile source and return if it is required
    if file == "compile_source":
        if not task["compile"]["source"]:
            flask.abort(404)
        logger.info("Returning compile source for task %s." % id)
        temp_file = tempfile.TemporaryFile(dir=config["data_dir"])
        temp_file.write(task["compile"]["source"])
        temp_file.seek(0)
        return flask.send_file(
            temp_file,
            cache_timeout=-1,
            as_attachment=True,
            attachment_filename=id + "_compile_source.zip",
            mimetype="application/zip"
        )
    # Else, convert it into bool indicating whether there is such file
    task["compile"]["source"] = bool(task["compile"]["source"])

    # Decompress execute data and return if it is required
    if file == "execute_data":
        if not task["execute"]["data"]:
            flask.abort(404)
        logger.info("Returning execute data for task %s." % id)
        temp_file = tempfile.TemporaryFile(dir=config["data_dir"])
        temp_file.write(task["execute"]["data"])
        temp_file.seek(0)
        return flask.send_file(
            temp_file,
            cache_timeout=-1,
            as_attachment=True,
            attachment_filename=id + "_execute_data.zip",
            mimetype="application/zip"
        )
    # Else, convert it into bool indicating whether there is such file
    task["execute"]["data"] = bool(task["execute"]["data"])

    logger.info("Decompressing all fields compressed by zlib of task %s." % id)
    # Deal with zlib decompressed filed in compile section
    task["compile"]["command"] = zlib.decompress(
        task["compile"]["command"]
    ).decode("utf-8") if task["compile"]["command"] else ""

    # Deal with zlib decompressed filed in execute section
    task["execute"]["input"] = zlib.decompress(
        task["execute"]["input"]
    ).decode("utf-8") if task["execute"]["input"] else ""
    task["execute"]["command"] = zlib.decompress(
        task["execute"]["command"]
    ).decode("utf-8") if task["execute"]["command"] else ""
    task["execute"]["standard"] = zlib.decompress(
        task["execute"]["standard"]
    ).decode("utf-8") if task["execute"]["standard"] else ""

    # Deal with zlib decompressed filed in result section
    if task["result"]:
        task["result"]["compile_output"] = zlib.decompress(
            task["result"]["compile_output"]
        ).decode("utf-8") if task["result"]["compile_output"] else ""
        task["result"]["compile_error"] = zlib.decompress(
            task["result"]["compile_error"]
        ).decode("utf-8") if task["result"]["compile_error"] else ""
        task["result"]["execute_output"] = zlib.decompress(
            task["result"]["execute_output"]
        ).decode("utf-8") if task["result"]["execute_output"] else ""
        task["result"]["execute_error"] = zlib.decompress(
            task["result"]["execute_error"]
        ).decode("utf-8") if task["result"]["execute_error"] else ""

    # Deal with time section
    task["add_time"] = "" if not task["add_time"] else task["add_time"].isoformat()
    task["report_time"] = "" if not task["report_time"] else task["report_time"].isoformat()

    logger.info("Returning task %s." % id)

    return flask.jsonify({"result": res.result, "task": task})


@server.route("/api/executors", methods=["GET"])
def api_executors():
    """
    Flask Handler: API Interface: Fetch executor list
    :return: Json containing executor list
    """
    # Fetch all executors from rpc and return
    logger.info("Getting executors.")
    res = select_from_etcd_and_call("executors", local_etcd, config["judicator_etcd_path"], logger)
    return flask.jsonify({
        "result": res.result,
        "executors": [{"id": x.id, "hostname": x.hostname, "report_time": x.report_time} for x in res.executors]
    })

@server.route("/api/judicators", methods=["GET"])
def api_judicators():
    """
    Flask Handler: API Interface: Fetch judicator list
    :return: Json containing judicator list
    """
    # Get from etcd and return
    logger.info("Getting judicators.")
    judicator = local_etcd.get(config["judicator_etcd_path"])
    return flask.jsonify({
        "result": ReturnCode.OK,
        "judicators": [{"name": k, "address": v} for k, v in judicator.items()]
    })

@server.route("/res/<path:path>", methods=["GET"])
def res(path):
    """
    Flask Handler: Serve a resource file
    :param path: Path to the file
    :return: The file
    """
    return flask.send_from_directory("webpage/res", path)

@server.route("/<path:page>", methods=["GET"])
def webpage(page):
    """
    Flask Handler: Serve a html template
    :param page: Name of the webpage
    :return: Rendered webpage
    """
    if page == "favicon.ico":
        return flask.send_from_directory("webpage/res", "icon/pylon.ico")
    args = flask.request.args.to_dict(flat=True)
    msg = {
        "message_title": args.get("message_title", ""),
        "message_content": args.get("message_content", ""),
        "message_type": args.get("message_type", "")
    }
    args.update(msg)
    return flask.render_template(page + ".html", **args)

@server.route("/", methods=["GET"])
def index():
    """
    Flask Handler: Serve the index
    :return: Rendered index
    """
    return flask.render_template("index.html", **flask.request.args)
