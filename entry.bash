#!/usr/bin/env bash

USAGE="USAGE: $0 ROLE [clean] [OPTIONS]\n\
Possible Role:\n\
  judicator\n\
  gateway\n\
  executor"

if [[ $# = 0 ]] ; then
    echo -e $USAGE
    exit 1
fi
if [[ "$1" != "judicator" ]] && [[ "$1" != "gateway" ]] && [[ "$1" != "executor" ]]; then
    echo -e $USAGE
    exit 1
fi
if [[ "$1" = "executor" ]]; then
    useradd -M -r -s /bin/false -c "Real executor user for all tasks" executor
fi
cd "$1"
if [[ "$2" = "clean" ]]; then
    bash clean.bash
    ln -s `pwd`/log /var/log/khala
    exec python boot.py "${@:3}"
else
    ln -s `pwd`/log /var/log/khala
    exec python boot.py "${@:2}"
fi
