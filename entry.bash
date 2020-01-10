#!/bin/bash

if [ "$1" = "executor" ]; then
    useradd -M -r -s /bin/false -c "Real executor for all tasks" executor
fi
cd "$1"
if [ "$2" = "clean" ]; then
    bash clean.bash
    exec python boot.py "${@:3}"
else
    exec python boot.py "${@:2}"
fi
