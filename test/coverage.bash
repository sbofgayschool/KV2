#!/bin/bash

bash clean.bash && \
coverage-3.7 run --rcfile=.coveragerc --concurrency=multiprocessing --parallel-mode $1 && \
coverage-3.7 combine && \
coverage-3.7 report && \
coverage-3.7 html
