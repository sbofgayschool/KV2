# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
import fcntl
import traceback


if __name__ == "__main__":
    print("============================")
    print("This script is going to add the lock on a batch of pid files,")
    print("and then open a child shell for you to carry out maintenance.")
    print("")
    pid_file = [x for x in input("Please input file names (separate by space):").split(" ") if x]
    print("")
    print("Trying to lock the pid files.")
    print("")
    try:
        file_list = []
        for f in pid_file:
            file_list.append(open(f, "r+"))
            fcntl.lockf(file_list[-1], fcntl.LOCK_EX)
            file_list[-1].seek(0, os.SEEK_SET)
        print("All pid file locked.")
        print("")
        print("Now a child shell is going to open. You can use the command:")
        print("kill -INT %s" % " ".join([f.read() for f in file_list]))
        print("to stop the processes first.")
        print("")
        print("Press ctrl-D to exit the child shell.")
        print("============================")
        print("")
        os.system("/bin/bash")
        print("")
        print("============================")
        print("Child shell terminated.")
        print("")
        for f in file_list:
            fcntl.lockf(f, fcntl.LOCK_UN)
            f.close()
        print("All pid files unlocked.")
    except Exception as e:
        print("Exception occurs during the process.")
        traceback.print_exc()
    print("")
    print("Maintenance script terminated.")
    print("============================")
    print("")
