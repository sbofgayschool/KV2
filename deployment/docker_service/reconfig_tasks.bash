#!/bin/bash

if [[ $# != 3 ]]; then
    echo -e "USAGE: $0 service-name task-number adjust-interval\n\
Possible Service:\n\
  judicator\n\
  gateway\n\
  executor"
    exit 1
fi

tasks=`docker service ps -q --filter "desired-state=running" $1`
if [[ $tasks == "no such service"* ]]; then
    echo "Service $1 not found."
    exit 1
fi

len=0
for t in $tasks; do
    len=$(($len+1))
done

if [[ $len -eq $(($2)) ]]; then
    echo "============================"
    echo "Service $1 is already running with $2 task(s)."
    echo "============================"
    echo ""
    exit 0
fi

echo "============================"
echo "Service $1 is going to be adjusted to $2 task(s)."
echo "============================"

if [[ $3 == "0" ]]; then
    if [[ $2 == "0" ]]; then
        echo ""
        echo "============================"
        echo "Removing service $1."
        echo "============================"
        echo ""
        docker service rm $1
    else
        echo ""
        echo "============================"
        echo "Adjust tasks number to $2."
        echo "============================"
        echo ""
        docker service scale $1=$2
    fi
else
    target=$(($2))
    if [[ $target -eq 0 ]]; then
        target=1
    fi
    if [[ $target -gt $len ]]; then
        delta=1
    else
        delta=-1
    fi
    for (( i=len; i != $target; i+=$delta )); do
        echo ""
        echo "============================"
        echo "Adjust tasks number to $(($i+$delta))."
        echo "============================"
        echo ""
        docker service scale $1=$(($i+$delta))
        echo ""
        echo "Wait for $3 seconds."
        sleep $3
    done
    if [[ $2 == "0" ]]; then
        echo ""
        echo "============================"
        echo "Removing service $1."
        echo "============================"
        echo ""
        docker service rm $1
        echo ""
        echo "Wait for $3 seconds."
        sleep $3
    fi
fi
echo ""
echo "============================"
echo "Task number of service $1 successfully adjusted."
echo "============================"
echo ""
