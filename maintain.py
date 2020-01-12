# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
import fcntl


if __name__ == "__main__":
    print("This script is going to add the lock on the pid file,")
    print("and then open a shell for you to carry out maintenance.")
    print("")
    pid_file = input("Please input the path to the pid file: ")
    print("")
    print("Trying to lock the pid file.")
    with open(pid_file, "r+") as f:
        fcntl.lockf(f, fcntl.LOCK_EX)
        print("Pid file locked.")
        print("")
        print("Now a bash is going to open. You can use the command:")
        f.seek(0, os.SEEK_SET)
        pid = f.read()
        print("kill -INT %s" % pid)
        print("to stop the process first.")
        print("Press ctrl-D to exit the terminal.")
        print("")
        print("==================================")
        print("")
        os.system("/bin/bash")
        print("")
        print("==================================")
        print("")
        print("Sub bash terminated.")
        fcntl.lockf(f, fcntl.LOCK_UN)
        print("Pid file unlocked.")
    print("")
    print("Maintenance script terminated.")
