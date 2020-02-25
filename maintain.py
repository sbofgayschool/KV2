# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os
import sys
import filelock
import traceback


if __name__ == "__main__":
    print("============================")
    print("This script is going to add the lock on a batch of pid files,")
    print("and then open a child shell for you to carry out maintenance.")
    print("")
    if len(sys.argv) == 1 or sys.argv[1] == "--help":
        print("USAGE: %s [pid files list]" % sys.argv[0])
    else:
        print("Trying to lock the pid files.")
        print("")
        pid_file, pid, locks = sys.argv[1: ], [], []
        try:
            for file in pid_file:
                locks.append(filelock.FileLock(file + ".lock"))
                locks[-1].acquire()
                try:
                    with open(file, "r") as f:
                        p = f.read()
                    if int(p) > 0:
                        pid.append(str(p))
                except:
                    print("Warning, file %s does not exist or it does not contain a valid pid." % file)
                    traceback.print_exc()
                    print("")
            print("All pid files locked.")
            print("")
            print("Now a child shell is going to open.")
            if pid:
                print("You can use the command:")
                print("kill -INT %s" % " ".join(pid))
                print("to stop the processes first.")
            print("")
            print("Press ctrl-D to exit the child shell.")
            print("++++++++++++++++++++++++++++")
            print("")
            os.system("/bin/bash")
            print("")
            print("++++++++++++++++++++++++++++")
            print("Child shell terminated.")
            print("")
        except Exception as e:
            print("Exception occurs during the process.")
            traceback.print_exc()
            print("")
        finally:
            for l in locks:
                l.release()
            print("All pid files unlocked.")
    print("")
    print("Maintenance script terminated.")
    print("============================")
    print("")