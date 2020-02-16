# -*- encoding: utf-8 -*-

__author__ = "chenty"

import json
import flask
import zlib
import tempfile
from os.path import join
import zipfile

from rpc.judicator_rpc.ttypes import *

from utility.function import get_logger
from utility.task import check_task_dict_size, check_id, decompress_and_truncate, TASK_DICTIONARY_MAX_SIZE, check_int
from utility.etcd.proxy import generate_local_etcd_proxy
from utility.rpc import select_from_etcd_and_call, extract, generate


# Server class inheriting Flask to serve HTTP request
class Server(flask.Flask):
    def __init__(self, module_name="Gateway", etcd_conf_path="config/etcd.json", uwsgi_conf_path="config/uwsgi.json"):
        """
        Initialize the object with logger and configuration
        :param module_name:
        :param etcd_conf_path:
        :param uwsgi_conf_path:
        """
        # Load configuration
        with open(uwsgi_conf_path, "r") as f:
            self.conf = json.load(f)["server"]
        self.module_name = module_name

        super().__init__(__name__, template_folder=self.conf["template"])

        # Generate a logger
        if "log" in self.conf:
            get_logger(self.logger, self.conf["log"]["info"], self.conf["log"]["error"])
        else:
            get_logger(self.logger, None, None)
        self.logger.info("%s server program started." % self.module_name)

        # Set flask configuration
        self.jinja_env.variable_start_string = "[["
        self.jinja_env.variable_end_string = "]]"
        self.config["MAX_CONTENT_LENGTH"] = TASK_DICTIONARY_MAX_SIZE

        # Generate proxy for etcd and mongodb
        with open(etcd_conf_path, "r") as f:
            self.local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], self.logger)

        self.load_response_function()
        return

    def load_response_function(self):
        """
        Load all flask response functions
        :return: None
        """
        @self.route("/api/test", methods=["GET"])
        def api_test():
            """
            Flask Handler: API Interface: Test if the gateway is working
            :return:
            """
            return flask.make_response("Khala gateway server is working.")

        @self.route("/api/task", methods=["POST"])
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
                if not (check_int(data["user"]) and
                        check_int(data["compile"]["timeout"]) and
                        check_int(data["execute"]["timeout"])):
                    raise Exception("An int parameter is out of bound.")
            except:
                self.logger.error("Failed to parse added task.", exc_info=True)
                return flask.jsonify({"result": ReturnCode.INVALID_INPUT, "id": None})

            self.logger.info("Generating all extra fields for added task.")
            # Deal with compile source
            compile_source = flask.request.files.get("compile_source")
            compile_source_str = flask.request.form.get("compile_source_str")
            compile_source_name = flask.request.form.get("compile_source_name")
            # If the zip file has been uploaded, use it
            # Else if some text is given, zipped it and use it
            if compile_source:
                self.logger.info("Detected compile source.")
                data["compile"]["source"] = compile_source.stream.read()
            elif compile_source_str and compile_source_name:
                self.logger.info("Detected compile source text.")
                # Create a temp dir
                temp_dir = tempfile.TemporaryDirectory(dir=self.conf["data_dir"])
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
                self.logger.info("Detected execute data.")
                data["execute"]["data"] = execute_data.stream.read()
            elif execute_data_str and execute_data_name:
                self.logger.info("Detected execute data text.")
                # Create a temp dir
                temp_dir = tempfile.TemporaryDirectory(dir=self.conf["data_dir"])
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

            self.logger.info("Generated all fields for added task.")

            # Check the size of the data before submit.
            if not check_task_dict_size(data):
                return flask.jsonify({"result": ReturnCode.TOO_LARGE, "id": None})

            # Add through rpc and return
            res = select_from_etcd_and_call(
                "add", self.local_etcd,
                self.conf["judicator_etcd_path"],
                self.logger,
                generate(data)
            )
            return flask.jsonify({"result": res.result, "id": res.id})

        @self.route("/api/task", methods=["DELETE"])
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
            self.logger.info("Canceling task %s." % id)
            res = select_from_etcd_and_call(
                "cancel",
                self.local_etcd,
                self.conf["judicator_etcd_path"],
                self.logger,
                id
            )
            return flask.jsonify({"result": res})

        @self.route("/api/task/list", methods=["GET"])
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
                self.logger.error("Failed to get all search conditions.", exc_info=True)
                return flask.jsonify(failed_result)

            self.logger.info("Parsed searching conditions.")

            # Search for the task
            res = select_from_etcd_and_call(
                "search",
                self.local_etcd,
                self.conf["judicator_etcd_path"],
                self.logger,
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
            self.logger.info("Found result: %s." % str([x["id"] for x in tasks]))
            for t in tasks:
                t["add_time"] = "" if not t["add_time"] else t["add_time"].isoformat()
                t["report_time"] = "" if not t["report_time"] else t["report_time"].isoformat()

            return flask.jsonify({"result": res.result, "pages": res.pages, "tasks": tasks})

        @self.route("/api/task", methods=["GET"])
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
            self.logger.info("Getting task %s." % id)
            res = select_from_etcd_and_call(
                "get",
                self.local_etcd,
                self.conf["judicator_etcd_path"],
                self.logger,
                id
            )
            # If not found, return
            # Otherwise return required data.
            if res.result != ReturnCode.OK:
                if file:
                    flask.abort(404)
                return flask.jsonify({"result": ReturnCode.NOT_EXIST, "task": None})

            task = extract(res.task)

            # If requesting files, try to fetch it
            if file:
                # Compile source and execute_data are in zip format
                # Others are plain text
                if file == "compile_source" or file == "execute_data":
                    postfix = ".zip"
                    mimetype = "application/zip"
                    content = task["compile"]["source"] if file == "compile_source" else task["execute"]["data"]
                else:
                    postfix = ".txt"
                    mimetype = "plain/text"
                    if file == "compile_command":
                        content = task["compile"]["command"]

                    elif file == "execute_input":
                        content = task["execute"]["input"]
                    elif file == "execute_command":
                        content = task["execute"]["command"]
                    elif file == "execute_standard":
                        content = task["execute"]["standard"]

                    else:
                        content = task.get("result", {}).get(file, b"")
                    if content:
                        content = zlib.decompress(content)
                # If nothing has been found, return 404
                if not content:
                    self.logger.warning("Returning 404 as %s is empty for task %s." % (file, id))
                    flask.abort(404)
                # Write a temp file and return it
                self.logger.info("Returning %s for task %s." % (file, id))
                temp_file = tempfile.TemporaryFile(dir=self.conf["data_dir"])
                temp_file.write(content)
                temp_file.seek(0)
                return flask.send_file(
                    temp_file,
                    cache_timeout=-1,
                    as_attachment=True,
                    attachment_filename=id + "_" + file + postfix,
                    mimetype=mimetype
                )

            # Deal with zip field
            task["compile"]["source"] = bool(task["compile"]["source"])
            task["execute"]["data"] = bool(task["execute"]["data"])

            self.logger.info("Decompressing all fields compressed by zlib of task %s." % id)
            # Deal with zlib decompressed field in compile section
            task["compile"]["command"] = decompress_and_truncate(task["compile"]["command"])

            # Deal with zlib decompressed field in execute section
            task["execute"]["input"] = decompress_and_truncate(task["execute"]["input"])
            task["execute"]["command"] = decompress_and_truncate(task["execute"]["command"])
            task["execute"]["standard"] = decompress_and_truncate(task["execute"]["standard"])

            # Deal with zlib decompressed field in result section
            if task["result"]:
                task["result"]["compile_output"] = decompress_and_truncate(task["result"]["compile_output"])
                task["result"]["compile_error"] = decompress_and_truncate(task["result"]["compile_error"])
                task["result"]["execute_output"] = decompress_and_truncate(task["result"]["execute_output"])
                task["result"]["execute_error"] = decompress_and_truncate(task["result"]["execute_error"])

            # Deal with time section
            task["add_time"] = "" if not task["add_time"] else task["add_time"].isoformat()
            task["report_time"] = "" if not task["report_time"] else task["report_time"].isoformat()

            self.logger.info("Returning task %s." % id)

            return flask.jsonify({"result": res.result, "task": task})

        @self.route("/api/executors", methods=["GET"])
        def api_executors():
            """
            Flask Handler: API Interface: Fetch executor list
            :return: Json containing executor list
            """
            # Fetch all executors from rpc and return
            self.logger.info("Getting executors.")
            res = select_from_etcd_and_call("executors", self.local_etcd, self.conf["judicator_etcd_path"], self.logger)
            return flask.jsonify({
                "result": res.result,
                "executors": [{"id": x.id, "hostname": x.hostname, "report_time": x.report_time} for x in res.executors]
            })

        @self.route("/api/judicators", methods=["GET"])
        def api_judicators():
            """
            Flask Handler: API Interface: Fetch judicator list
            :return: Json containing judicator list
            """
            # Get from etcd and return
            self.logger.info("Getting judicators.")
            judicator = self.local_etcd.get(self.conf["judicator_etcd_path"])
            return flask.jsonify({
                "result": ReturnCode.OK,
                "judicators": [{"name": k, "address": v} for k, v in judicator.items()]
            })

        @self.route("/res/<path:path>", methods=["GET"])
        def res(path):
            """
            Flask Handler: Serve a resource file
            :param path: Path to the file
            :return: The file
            """
            return flask.send_from_directory("webpage/res", path)

        @self.route("/<path:page>", methods=["GET"])
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

        @self.route("/", methods=["GET"])
        def index():
            """
            Flask Handler: Serve the index
            :return: Rendered index
            """
            return flask.render_template("index.html", **flask.request.args)

        return

    def __del__(self):
        """
        Destructor for Server class
        :return: None
        """
        self.logger.info("%s server program exiting." % self.module_name)
        return

# Get the server object for uwsgi
server = Server()
