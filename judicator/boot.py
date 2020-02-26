#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2020 SBofGaySchoolBuPaAnything
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

__author__ = "chenty"

# Add current folder and parent folder into python path
import os
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()
os.environ["PYTHONPATH"] += ":" + os.path.dirname(os.getcwd())
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.getcwd()))
import signal

from utility.etcd.daemon import command_parser as etcd_parser
from utility.mongodb.daemon import command_parser as mongodb_parser
from judicator.main import command_parser as main_parser
from utility.boot.daemon import sigterm_handler, run


# Register a signal for cleanup
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == "__main__":
    service_list = [{
        "name": "etcd",
        "config_template": "config/templates/etcd.json",
        "config": "config/etcd.json",
        "args_parser": etcd_parser
    }, {
        "name": "mongodb",
        "config_template": "config/templates/mongodb.json",
        "config": "config/mongodb.json",
        "args_parser": mongodb_parser
    }, {
        "name": "main",
        "config_template": "config/templates/main.json",
        "config": "config/main.json",
        "args_parser": main_parser
    }]
    run(service_list, "Judicator", "Judicator of Khala system. Handle requests and maintain task data.")
