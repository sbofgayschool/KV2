#!/bin/bash

if [ "$1" = "executor" ]; then
    useradd -M -r -s /bin/false -c "Real executor for all tasks" executor
fi

cd "$1"
python boot.py "${@:2}"
