# -*- encoding: utf-8 -*-

__author__ = "chenty"

import os


LOCAL_TEST = True

if __name__ == "__main__":
    os.environ["PYTHONPATH"] += ":" + os.getcwd()
    if LOCAL_TEST:
        os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())
        print(os.environ["PYTHONPATH"])