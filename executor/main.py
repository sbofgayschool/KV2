# -*- encoding: utf-8 -*-

__author__ = "chenty"

from jsoncomment import JsonComment
json = JsonComment()

import os
from os.path import join
import shutil
import threading
import time
import zipfile
import zlib
import subprocess

from rpc.judicator_rpc.ttypes import ReturnCode

from utility.function import get_logger, try_with_times, check_empty_dir, check_task_dict_size
from utility.etcd import generate_local_etcd_proxy
from utility.rpc import extract, generate, select_from_etcd_and_call
from utility.define import TASK_STATUS


def change_user():
    """
    Change user of subprocess according to given configuration
    :return: None
    """
    os.setgid(config["task"]["user"]["gid"])
    os.setuid(config["task"]["user"]["uid"])
    return

def execute(id):
    """
    Target function for execute daemon threads
    Execute a job
    :param id: Job id
    :return: None
    """
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
        os.mkdir(work_dir)
        os.mkdir(download_dir)
        os.mkdir(source_dir)
        os.mkdir(data_dir)
        os.mkdir(result_dir)

        logger.info("Task %s generating dirs complete." % task["id"])

        # Generate all files for compilation
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
            ["chown", str(config["task"]["user"]["uid"]) + ":" + str(config["task"]["user"]["gid"]), "-R", source_dir]
        ).wait()
        logger.info("Task %s generating needed file complete." % task["id"])
    except:
        logger.error("Task %s generating dirs and files failed." % task["id"], exc_info=True)
        cancel = True

    # Start to compile
    # Acquire the lock
    lock.acquire()
    cancel = cancel or task["cancel"]
    # If not cancelled, start subprocess to compile it
    # Otherwise, clean and exit
    try:
        if not cancel:
            logger.info("Task %s starting to compile." % task["id"])
            task["status"] = TASK_STATUS["COMPILING"]
            with open(compile_output, "wb") as ostream, open(compile_error, "wb") as estream:
                task["process"] = subprocess.Popen(
                    ["bash", config["task"]["compile"]["command"]],
                    stdout=ostream,
                    stderr=estream,
                    cwd=source_dir,
                    preexec_fn=change_user
                )
        else:
            task["done"] = True
    except:
        logger.error("Error occurs when trying to start compilation of task %s." % task["id"], exc_info=True)
        cancel = True
    finally:
        # Lock must be released
        lock.release()
        if cancel:
            logger.info("Task %s exiting." % task["id"])
            shutil.rmtree(work_dir)
            return

    # Wait for the compilation with timeout
    try:
        res = task["process"].wait(task["compile"]["timeout"])
        success = res == 0
        logger.info("Task %s finished compiling with exit code %d." % (task["id"], res))
    except:
        logger.warning("Task %s failed to compile." % task["id"], exc_info=True)
        # If timeout, kill and wait for the subprocess
        success = False
        task["result"]["compile_error"] = b"Compile time out."
        task["process"].kill()
        task["process"].wait()

    # Start to execute
    # Acquire the lock
    lock.acquire()
    # If compilation is success, start subprocess to compile it
    # Otherwise, clean and exit
    try:
        # Add compile result
        with open(compile_output, "rb") as f:
            task["result"]["compile_output"] = zlib.compress(f.read())
        if not compile_error:
            with open(compile_error, "rb") as f:
                task["result"]["compile_error"] = zlib.compress(f.read())
        # If the compilation output goes beyond the limitation
        if not check_task_dict_size(task):
            task["result"]["compile_output"] = b""
            task["result"]["compile_error"] = b"Compile output limitation exceeded."
            success = False
        # If compilation is successful, execute it
        if success:
            logger.info("Task %s start to run." % task["id"])
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
                    preexec_fn=change_user
                )
    except:
        logger.error(
            "Error occurs when trying to collect compilation result and start execution of task %s." % task["id"],
            exc_info=True
        )
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
            logger.info("Task %s exiting." % task["id"])
            shutil.rmtree(work_dir)
            return

    # Wait for the execution with timeout
    try:
        res = task["process"].wait(task["execute"]["timeout"])
        success = res == 0
        logger.info("Task %s finished running with exit code %d." % (task["id"], res))
    except:
        logger.warning("Task %s failed to run." % task["id"], exc_info=True)
        # If timeout, kill and wait for the subprocess
        success = False
        task["result"]["execute_error"] = b"Execution time out."
        task["process"].kill()
        task["process"].wait()

    # Adjust task status accordingly
    # Acquire the lock first
    lock.acquire()
    try:
        # Add execution result
        with open(execute_output, "rb") as f:
            task["result"]["execute_output"] = zlib.compress(f.read())
        if not task["result"]["execute_error"]:
            with open(execute_error, "rb") as f:
                task["result"]["execute_error"] = zlib.compress(f.read())
        # If the execution output goes beyond the limitation
        if not check_task_dict_size(task):
            task["result"]["execute_output"] = b""
            task["result"]["execute_error"] = b"Execution output limitation exceeded."
            success = False
        task["status"] = TASK_STATUS["SUCCESS"] if success else TASK_STATUS["RUN_FAILED"]
    except:
        logger.error("Error occurs when trying to collect execution result of task %s." % task["id"], exc_info=True)
        task["status"] = TASK_STATUS["RUN_FAILED"]
    finally:
        task["done"] = True
        task["process"] = None
        # Lock must be released
        lock.release()

    logger.info("Task %s exiting." % task["id"])
    # Clean files
    shutil.rmtree(work_dir)

    return

def report(complete, executing, vacant):
    """
    Get the address of a judicator and report the tasks status
    :param complete: Complete task list
    :param executing: Executing task list
    :param vacant: Vacant task places
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

if __name__ == "__main__":
    # Load configuration
    with open("config/main.json", "r") as f:
        config = json.load(f)
    retry_times = config["retry"]["times"]
    retry_interval = config["retry"]["interval"]

    # Generate a logger
    if "log" in config:
        logger = get_logger(
            "main",
            config["log"]["info"],
            config["log"]["error"]
        )
    else:
        logger = get_logger("main", None, None)
    logger.info("Executor main program started.")

    # Generate proxy for etcd
    with open("config/etcd.json", "r") as f:
        local_etcd = generate_local_etcd_proxy(json.load(f)["etcd"], logger)

    # Check whether the data dir of main is empty
    # If not, delete it and create a new one
    if not check_empty_dir(config["data_dir"]):
        logger.info("Delete previous existing data directory and create a new one.")
        shutil.rmtree(config["data_dir"])
        os.mkdir(config["data_dir"])
        os.chmod(config["data_dir"], 0o700)

    # If task user id and group id is not specified, use the current user and group
    if "user" not in config["task"]:
        config["task"]["user"] = {"uid": os.getuid(), "gid": os.getgid()}
    logger.info(
        "Task execution is going to use uid %d and gid %d" % (
            config["task"]["user"]["uid"],
            config["task"]["user"]["gid"]
        )
    )

    tasks = {}
    lock = threading.Lock()

    # Report tasks execution status regularly
    while True:
        try:
            time.sleep(config["report_interval"])

            # Collect things to report
            logger.info("Start to collect report contents.")
            complete, executing = [], []
            vacant = config["task"]["vacant"]
            try:
                # Acquire lock first before modifying global variable
                lock.acquire()
                try:
                    for t in tasks:
                        if not tasks[t]["cancel"]:
                            if tasks[t]["thread"] and not tasks[t]["thread"].is_alive():
                                logger.info("Task %s added to complete list." % t)
                                complete.append(generate(tasks[t], False, False, False))
                            else:
                                logger.info("Task %s added to executing list." % t)
                                executing.append(generate(tasks[t], True))
                                vacant -= 1
                except:
                    logger.error("Error during report content collection.", exc_info=True)
                finally:
                    # Lock must be released
                    lock.release()
            except:
                logger.error("Fatal exception during report content collection.", exc_info=True)

            # Try to report to judicator and get response
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
                vacant
            )
            if not success:
                logger.error("Failed to report to judicator, skipping tasks update.")
                continue
            cancel, assign = [extract(x, brief=True) for x in res[0]], [extract(x) for x in res[1]]
            logger.debug("Get cancel list %s." % cancel)
            logger.debug("Get assign list %s." % assign)

            # Update tasks information
            logger.info("Try to update tasks information.")
            try:
                # Acquire lock first before modifying global variable
                lock.acquire()
                try:
                    # Cancel tasks
                    for t in cancel:
                        logger.info("Task %s is going to be cancelled." % t)
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
                    for t in tasks_list:
                        if tasks[t]["thread"] and not tasks[t]["thread"].is_alive():
                            # A task is can only be considered as all done (thus can be deleted)
                            # when thread.is_alive() is False (indicating the daemon thread has finished)
                            # and cancel (indicating the judicator has received the result) is True
                            if tasks[t]["cancel"]:
                                logger.info("Delete task %s." % t)
                                del tasks[t]

                    # Handle newly assigned
                    for t in assign:
                        logger.info("Newly assigned task %s." % t)

                        tasks[t["id"]] = t
                        tasks[t["id"]]["process"] = None
                        tasks[t["id"]]["cancel"] = False

                        # Generate a thread and start it
                        tasks[t["id"]]["thread"] = threading.Thread(target=execute, args=(t["id"], ))
                        tasks[t["id"]]["thread"].setDaemon(True)
                        tasks[t["id"]]["thread"].start()
                except:
                    logger.error("Error during task update.", exc_info=True)
                finally:
                    # Lock must be released
                    lock.release()
            except:
                logger.error("Fatal exception during task update.", exc_info=True)

            logger.info("Routine work finished.")

        except KeyboardInterrupt:
            logger.info("Received SIGINT.")
            break

    logger.info("Exiting.")