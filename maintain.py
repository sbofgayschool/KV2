# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
import fcntl
import traceback


if __name__ == "__main__":
    print("============================")
    print("This script is going to add the lock on the pid file,")
    print("and then open a child shell for you to carry out maintenance.")
    print("")
    pid_file = input("Please input the path to the pid file: ")
    print("")
    print("============================")
    print("Trying to lock the pid file.")
    try:
        with open(pid_file, "r+") as f:
            fcntl.lockf(f, fcntl.LOCK_EX)
            f.seek(0, os.SEEK_SET)
            pid = f.read()
            print("Pid file locked.")
            print("")
            print("Now a child shell is going to open. You can use the command:")
            print("kill -INT %s" % pid)
            print("to stop the process first.")
            print("")
            print("You may also wish to run this script again inside the child shell")
            print("to lock another pid file.")
            print("")
            print("Press ctrl-D to exit the child shell.")
            print("============================")
            print("")
            print("++++++++++++++++++++++++++++")
            print("")
            os.system("/bin/bash")
            print("")
            print("++++++++++++++++++++++++++++")
            print("")
            print("============================")
            print("Child shell terminated.")
            fcntl.lockf(f, fcntl.LOCK_UN)
            print("Pid file unlocked.")
    except Exception as e:
        print("Exception occurs during the process.")
        traceback.print_exc()
    print("")
    print("Maintenance script terminated.")
    print("============================")
    print("")
