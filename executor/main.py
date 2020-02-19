# -*- encoding: utf-8 -*-

__author__ = "chenty"

import json
import os
from os.path import join
import shutil
import threading
import time
import zipfile
import zlib
import subprocess
import socket
import grp
import pwd

from rpc.judicator_rpc.ttypes import ReturnCode

from utility.function import get_logger, try_with_times, check_empty_dir
from utility.task import TASK_STATUS, check_task_dict_size
from utility.etcd.proxy import generate_local_etcd_proxy
from utility.rpc import extract, generate, select_from_etcd_and_call


# Global dictionary for all tasks
tasks = {}
# The lock for the dictionary
lock = threading.Lock()

def change_user(config):
    """
    A wrapper for changing user of subprocess according to given configuration
    :param config: The configuration json
    :return: Wrapped function
    """
    def change():
        """
        Change the user for subprocess
        :return: None
        """
        os.setgid(config["task"]["user"]["gid"])
        os.setuid(config["task"]["user"]["uid"])
        return
    return change

def execute(id, config, logger):
    """
    Target function for execute daemon threads
    Execute a job
    :param id: Job id
    :param config: Configuration json
    :param logger: The logger object
    :return: None
    """
    global tasks, lock

    logger.info("Working thread for task %s started." % id)
    # Get the specified task
    task = tasks[id]
    task["result"] = {
        "compile_output": b"",
        "compile_error": b"",
        "execute_output": b"",
        "execute_error": b""
    }
    cancel = False

    work_dir = join(config["data_dir"], task["id"])
    download_dir = join(work_dir, config["task"]["dir"]["download"])
    source_dir = join(work_dir, config["task"]["dir"]["source"])
    data_dir = join(work_dir, config["task"]["dir"]["data"])
    result_dir = join(work_dir, config["task"]["dir"]["result"])

    compile_source = join(download_dir, config["task"]["compile"]["source"])
    compile_command = join(source_dir, config["task"]["compile"]["command"])
    compile_output = join(result_dir, config["task"]["compile"]["output"])
    compile_error = join(result_dir, config["task"]["compile"]["error"])

    execute_input = join(source_dir, config["task"]["execute"]["input"])
    execute_data = join(download_dir, config["task"]["execute"]["data"])
    execute_command = join(source_dir, config["task"]["execute"]["command"])
    execute_output = join(result_dir, config["task"]["execute"]["output"])
    execute_error = join(result_dir, config["task"]["execute"]["error"])

    # Create all dirs and files
    try:
        # Create all necessary dirs and unzip sources
        logger.info("Generating directories for task %s." % task["id"])
        os.mkdir(work_dir)
        os.mkdir(download_dir)
        os.mkdir(source_dir)
        os.mkdir(data_dir)
        os.mkdir(result_dir)

        # Generate all files for compilation
        logger.info("Generating files for task %s." % task["id"])
        # Compile source
        if task["compile"]["source"]:
            with open(compile_source, "wb") as f:
                f.write(task["compile"]["source"])
            with zipfile.ZipFile(compile_source, "r") as f:
                f.extractall(source_dir)
        # Compile command
        with open(compile_command, "wb") as f:
            if task["compile"]["command"]:
                f.write(zlib.decompress(task["compile"]["command"]))

        # Generate all files for execution
        # Execute input
        with open(execute_input, "wb") as f:
            if task["execute"]["input"]:
                f.write(zlib.decompress(task["execute"]["input"]))
        # Execute data
        if task["execute"]["data"]:
            with open(execute_data, "wb") as f:
                f.write(task["execute"]["data"])
            with zipfile.ZipFile(execute_data, "r") as f:
                f.extractall(data_dir)
        # Execute command
        with open(execute_command, "wb") as f:
            if task["execute"]["command"]:
                f.write(zlib.decompress(task["execute"]["command"]))
        # Changing the owner of source dir
        subprocess.Popen(
            ["chown", "-R", str(config["task"]["user"]["uid"]) + ":" + str(config["task"]["user"]["gid"]), source_dir]
        ).wait()
        logger.info("Generated all directories and files for task %s." % task["id"])
    except:
        logger.error("Failed to generate directories and files for task %s." % task["id"], exc_info=True)
        cancel = True

    # Start to compile
    # Acquire the lock
    lock.acquire()
    cancel = cancel or task["cancel"]
    # If not cancelled, start subprocess to compile it
    # Otherwise, clean and exit
    try:
        if not cancel:
            logger.info("Compiling task %s." % task["id"])
            task["status"] = TASK_STATUS["COMPILING"]
            with open(compile_output, "wb") as ostream, open(compile_error, "wb") as estream:
                task["process"] = subprocess.Popen(
                    ["bash", config["task"]["compile"]["command"]],
                    stdout=ostream,
                    stderr=estream,
                    cwd=source_dir,
                    preexec_fn=change_user(config)
                )
        else:
            task["done"] = True
    except:
        logger.error("Failed to compile task %s." % task["id"], exc_info=True)
        cancel = True
    finally:
        # Lock must be released
        lock.release()
        if cancel:
            logger.info("Working thread for task %s terminating." % task["id"])
            shutil.rmtree(work_dir)
            return

    # Wait for the compilation with timeout
    try:
        res = task["process"].wait(task["compile"]["timeout"])
        success = res == 0
        logger.info("Compiled task %s with exit code %d." % (task["id"], res))
    except Exception as e:
        # Check if it is timed out or something else happened
        if isinstance(e, subprocess.TimeoutExpired):
            logger.warning("Exceeded time limit when compiling task %s." % task["id"], exc_info=True)
            task["result"]["compile_error"] = zlib.compress(b"Compile time out.")
        else:
            logger.error("Failed to finish compilation of task %s." % task["id"], exc_info=True)
            task["result"]["compile_error"] = zlib.compress(b"Unknown error.")
        # Kill and wait for the subprocess
        success = False
        task["process"].kill()
        task["process"].wait()

    # Start to execute
    # Acquire the lock
    lock.acquire()
    # If compilation is success, start subprocess to compile it
    # Otherwise, clean and exit
    try:
        # Add compile result
        logger.info("Collecting compilation result for task %s." % task["id"])
        with open(compile_output, "rb") as f:
            task["result"]["compile_output"] = zlib.compress(f.read())
        if not task["result"]["compile_error"]:
            with open(compile_error, "rb") as f:
                task["result"]["compile_error"] = zlib.compress(f.read())
        # If the compilation output goes beyond the limitation
        tmp_task = dict(task)
        tmp_task.pop("process", None)
        tmp_task.pop("thread", None)
        if not check_task_dict_size(tmp_task):
            task["result"]["compile_output"] = b""
            task["result"]["compile_error"] = zlib.compress(b"Compile output limitation exceeded.")
            success = False
        # If compilation is successful, execute it
        if success:
            logger.info("Running task %s." % task["id"])
            task["status"] = TASK_STATUS["RUNNING"]
            with open(execute_input, "rb") as istream, \
                    open(execute_output, "wb") as ostream, \
                    open(execute_error, "wb") as estream:
                task["process"] = subprocess.Popen(
                    ["bash", config["task"]["execute"]["command"]],
                    stdin=istream,
                    stdout=ostream,
                    stderr=estream,
                    cwd=source_dir,
                    preexec_fn=change_user(config)
                )
    except:
        logger.error("Failed to collect compilation result or run task %s." % task["id"], exc_info=True)
        success = False
    finally:
        # It not successful, set status to compile failed
        if not success:
            task["status"] = TASK_STATUS["COMPILE_FAILED"]
            task["done"] = True
            task["process"] = None
        # Lock must be released
        lock.release()
        # It not successful, clean and exit
        if not success:
            logger.info("Working thread for task %s terminating." % task["id"])
            shutil.rmtree(work_dir)
            return

    # Wait for the execution with timeout
    try:
        res = task["process"].wait(task["execute"]["timeout"])
        success = res == 0
        logger.info("Run task %s with exit code %d." % (task["id"], res))
    except Exception as e:
        # Check if it is timed out or something else happened
        if isinstance(e, subprocess.TimeoutExpired):
            logger.warning("Exceeded time limit when running task %s." % task["id"], exc_info=True)
            task["result"]["execute_error"] = zlib.compress(b"Execution time out.")
        else:
            logger.error("Failed to finish execution of task %s." % task["id"], exc_info=True)
            task["result"]["execute_error"] = zlib.compress(b"Unknown error.")
        # Kill and wait for the subprocess
        success = False
        task["process"].kill()
        task["process"].wait()

    # Adjust task status accordingly
    # Acquire the lock first
    lock.acquire()
    try:
        # Add execution result
        logger.info("Collecting execution result.")
        with open(execute_output, "rb") as f:
            task["result"]["execute_output"] = zlib.compress(f.read())
        if not task["result"]["execute_error"]:
            with open(execute_error, "rb") as f:
                task["result"]["execute_error"] = zlib.compress(f.read())
        # If the execution output goes beyond the limitation
        tmp_task = dict(task)
        tmp_task.pop("process", None)
        tmp_task.pop("thread", None)
        if not check_task_dict_size(tmp_task):
            task["result"]["execute_output"] = b""
            task["result"]["execute_error"] = zlib.compress(b"Execution output limitation exceeded.")
            success = False
        task["status"] = TASK_STATUS["SUCCESS"] if success else TASK_STATUS["RUN_FAILED"]
    except:
        logger.error("Failed to collect execution result of task %s." % task["id"], exc_info=True)
        task["status"] = TASK_STATUS["RUN_FAILED"]
    finally:
        task["done"] = True
        task["process"] = None
        # Lock must be released
        lock.release()

    logger.info("Working thread for task %s terminating." % task["id"])
    # Clean files
    shutil.rmtree(work_dir)

    return

def report(complete, executing, vacant, local_etcd, config, logger):
    """
    Get the address of a judicator and report the tasks status
    :param complete: Complete task list
    :param executing: Executing task list
    :param vacant: Vacant task places
    :param local_etcd: Proxy of local etcd
    :param config: Configuration json
    :param logger: Logger object
    :return: Tuple contain RPC report return
    """
    res = select_from_etcd_and_call(
        "report",
        local_etcd,
        config["judicator_etcd_path"],
        logger,
        config["name"],
        complete,
        executing,
        vacant
    )
    if res.result != ReturnCode.OK:
        raise Exception("Return code from judicator is not 0 but %d." % res.result)
    return res.cancel, res.assign

def run(module_name="Executor", etcd_conf_path="config/etcd.json", main_conf_path="config/main.json"):
    """
    Load config and run executor main program
    :param module_name: Name of the caller module
    :param etcd_conf_path: Path to etcd config file
    :param main_conf_path: Path to main config file
    :return: None
    """
    global tasks, lock

    # Load configuration
    with open(main_conf_path, "r") as f:
        config = json.load(f)
    retry_times = config["retry"]["times"]
    retry_interval = config["retry"]["interval"]

    # Generate logger
    if "log" in config:
        logger = get_logger("main", config["log"]["info"], config["log"]["error"])
    else:
        logger = get_logger("main", None, None)
    logger.info("%s main program started." % module_name)

    # Generate proxy for local etcd
    with open(etcd_conf_path, "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)

    # Check whether the data dir of main is empty
    # If not, delete it and create a new one
    if not check_empty_dir(config["data_dir"]):
        shutil.rmtree(config["data_dir"])
        os.mkdir(config["data_dir"])
        os.chmod(config["data_dir"], 0o700)
        logger.info("Previous data directory deleted with a new one created.")

    # If task user id and group id is not specified, use the current user and group
    if "user" not in config["task"]:
        config["task"]["user"] = {"uid": os.getuid(), "gid": os.getgid()}
    logger.info("Task execution uid: %d, gid: %d." % (config["task"]["user"]["uid"], config["task"]["user"]["gid"]))

    # Report tasks execution status regularly
    logger.info("Starting executor routines.")
    while True:
        try:
            time.sleep(config["report_interval"])

            # Collect things to report
            logger.info("Collecting report content.")
            complete, executing = [], []
            vacant = config["task"]["vacant"]
            try:
                # Acquire lock first before modifying global variable
                lock.acquire()
                try:
                    for t in tasks:
                        if not tasks[t]["cancel"]:
                            if tasks[t]["thread"] and not tasks[t]["thread"].is_alive():
                                complete.append(generate(tasks[t], False, False, False))
                                logger.info("Task %s added to complete list." % t)
                            else:
                                executing.append(generate(tasks[t], True))
                                vacant -= 1
                                logger.info("Task %s added to executing list." % t)
                except:
                    logger.error("Failed to collect report content.", exc_info=True)
                finally:
                    # Lock must be released
                    lock.release()
            except:
                logger.error("Failed to obtain lock for report content collection.", exc_info=True)

            # Try to report to judicator and get response
            logger.info("Executor current vacancy: %d." % vacant)
            logger.info("Reporting to judicator.")
            success, res = try_with_times(
                retry_times,
                retry_interval,
                False,
                logger,
                "report to judicator",
                report,
                complete,
                executing,
                vacant,
                local_etcd,
                config,
                logger
            )
            if not success:
                logger.error("Failed to report to judicator. Skipping tasks update.")
                continue
            cancel, assign = [extract(x, brief=True) for x in res[0]], [extract(x) for x in res[1]]
            logger.info("Reported to judicator with response:")
            logger.info("Cancel list: %s." % str([t["id"] for t in cancel]))
            logger.info("Assign list: %s." % str([t["id"] for t in assign]))

            # Update tasks information
            logger.info("Updating tasks information.")
            try:
                # Acquire lock first before modifying global variable
                lock.acquire()
                try:
                    # Cancel tasks
                    logger.info("Checking tasks to be cancelled.")
                    for t in cancel:
                        logger.info("Cancelling task %s." % t["id"])
                        if not t["id"] in tasks:
                            continue
                        tasks[t["id"]]["cancel"] = True
                        # If the subprocess is still running, kill it
                        if tasks[t["id"]]["process"] and tasks[t["id"]]["process"].poll() is None:
                            logger.info("Killing subprocess of task %s." % t["id"])
                            tasks[t["id"]]["process"].kill()
                        else:
                            logger.info("No subprocess to kill for task %s." % t["id"])

                    # Clean all tasks
                    # A list ot tasks index must be built beforehand, as the tasks is going to change
                    tasks_list = tuple(tasks.keys())
                    logger.info("Checking tasks to be deleted.")
                    for t in tasks_list:
                        if tasks[t]["thread"] and not tasks[t]["thread"].is_alive():
                            # A task is can only be considered as all done (thus can be deleted)
                            # when thread.is_alive() is False (indicating the daemon thread has finished)
                            # and cancel (indicating the judicator has received the result) is True
                            if tasks[t]["cancel"]:
                                del tasks[t]
                                logger.info("Deleted task %s." % t)

                    # Handle newly assigned
                    logger.info("Checking tasks to be assigned.")
                    for t in assign:
                        logger.info("Assigned task %s." % t["id"])

                        tasks[t["id"]] = t
                        tasks[t["id"]]["process"] = None
                        tasks[t["id"]]["cancel"] = False

                        # Generate a thread and start it
                        tasks[t["id"]]["thread"] = threading.Thread(target=execute, args=(t["id"], config, logger))
                        tasks[t["id"]]["thread"].setDaemon(True)
                        tasks[t["id"]]["thread"].start()
                except:
                    logger.error("Failed to update tasks.", exc_info=True)
                finally:
                    # Lock must be released
                    lock.release()
            except:
                logger.error("Failed to obtain lock for task updating.", exc_info=True)

            logger.info("Finished executor routine work.")

        except KeyboardInterrupt:
            logger.info("Received SIGINT.")
            break

    logger.info("%s main program exiting." % module_name)
    return

def command_parser(parser):
    """
    Add executor main args to args parser
    :param parser: The args parser
    :return: Callback function to modify config
    """
    # Add needed args
    parser.add_argument("--main-name", dest="main_name", default=None,
                        help="Name of the executor")
    parser.add_argument("--main-task-vacant", type=int, dest="main_task_vacant", default=None,
                        help="Capacity of tasks of the executor")
    parser.add_argument("--main-report-interval", type=int, dest="main_report_interval", default=None,
                        help="Interval between reports made to judicator from executor")
    parser.add_argument("--main-task-user-group", dest="main_task_user_group", default=None,
                        help="User:group string indicating execution user/group when executing real tasks.")
    parser.add_argument("--main-print-log", dest="main_print_log", action="store_const", const=True, default=False,
                        help="Print the log of main module to stdout")

    def conf_generator(args, config_sub, client, services, start_order):
        """
        Callback function to modify executor main configuration according to parsed args
        :param args: Parse args
        :param config_sub: Template config
        :param client: Docker client
        :param services: Dictionary of services
        :param start_order: List of services in starting order
        :return: None
        """
        # Modify config by parsed args
        if args.retry_times is not None:
            config_sub["retry"]["times"] = args.retry_times
        if args.retry_interval is not None:
            config_sub["retry"]["interval"] = args.retry_interval
        if args.main_name is not None:
            if args.main_name == "ENV":
                config_sub["name"] = os.environ.get("NAME")
            else:
                config_sub["name"] = args.main_name
        if args.main_task_vacant is not None:
            config_sub["task"]["vacant"] = args.main_task_vacant
        if args.main_task_user_group is not None:
            user, group = args.main_task_user_group.split(':')
            config_sub["task"]["user"] = {"uid": pwd.getpwnam(user)[2], "gid": grp.getgrnam(group)[2]}
        if args.main_report_interval is not None:
            config_sub["report_interval"] = args.main_report_interval
        if args.main_print_log:
            config_sub.pop("log", None)
        if args.docker_sock is not None:
            config_sub["docker_sock"] = args.docker_sock
            config_sub["task"]["user"] = {"uid": pwd.getpwnam("executor")[2], "gid": grp.getgrnam("executor")[2]}
            if args.main_name is None:
                config_sub["name"] = socket.gethostname()

        # Generate information for execution
        services["main"] = {
            "pid_file": config_sub["pid_file"],
            "command": config_sub["exe"],
            "process": None
        }
        start_order.append("main")
        return

    return conf_generator

if __name__ == "__main__":
    run()
