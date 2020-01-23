#!/bin/bash

KHALA='comradestukov/khala:v0.1'

NETWORK='khala'

JUDICATOR='judicator'
EXECUTOR='executor'
GATEWAY='gateway'

COOL_DOWN_TIME="25"

if [[ $# < 3 ]] || [[ $# > 4 ]]; then
    echo "USAGE: $0 judicator-number gateway-number executor-number [--output-log]"
    exit 1
fi

if [[ $# == 4 ]] && [[ $4 == "--output-log" ]]; then
    JUDICATOR_PRINT_FLAG="--boot-print-log --etcd-print-log --mongodb-print-log --main-print-log"
    GATEWAY_PRINT_FLAG="--boot-print-log --etcd-print-log --uwsgi-print-log"
    EXECUTOR_PRINT_FLAG="--boot-print-log --etcd-print-log --main-print-log"
else
    JUDICATOR_PRINT_FLAG=""
    GATEWAY_PRINT_FLAG=""
    EXECUTOR_PRINT_FLAG=""
fi

echo "============================"
echo "Creating following services:"
echo "$JUDICATOR : $1 $JUDICATOR_PRINT_FLAG"
echo "$GATEWAY : $2 $GATEWAY_PRINT_FLAG"
echo "$EXECUTOR : $3 $EXECUTOR_PRINT_FLAG"
echo "============================"
echo ""

echo "============================"
echo "Creating network."
echo "============================"
echo ""
if [[ `docker network ls --filter="name=$NETWORK" -q` == "" ]]; then
    docker network create -d overlay --attachable khala
else
    echo "Network $NETWORK already exists."
fi

echo ""
echo "============================"
echo "Creating first $JUDICATOR service."
echo "============================"
echo ""

docker service create \
--stop-grace-period=30s \
--replicas 1 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network $NETWORK \
--env NAME={{.Service.Name}}.{{.Task.Slot}} \
--name $JUDICATOR $KHALA judicator \
--docker-sock=unix:///var/run/docker.sock \
$JUDICATOR_PRINT_FLAG \
--etcd-cluster-join-service=$JUDICATOR \
--etcd-advertise-address=DOCKER \
--mongodb-advertise-address=DOCKER \
--main-advertise-address=DOCKER \
--etcd-name=ENV \
--mongodb-name=ENV \
--main-name=ENV

if [[ $1 != "1" ]]; then
    echo ""
    echo "============================"
    echo "Scaling service $JUDICATOR to $1."
    echo "============================"
    echo ""
    docker service scale $JUDICATOR=$1
fi

if [[ $2 != "0" ]]; then
    echo ""
    echo "============================"
    echo "Creating service $GATEWAY."
    echo "============================"
    echo ""

    docker service create \
    --stop-grace-period=30s \
    --replicas $2 \
    --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
    --network $NETWORK -p 7000:7000 \
    --env NAME={{.Service.Name}}.{{.Task.Slot}} \
    --name $GATEWAY $KHALA gateway \
    --docker-sock=unix:///var/run/docker.sock \
    $GATEWAY_PRINT_FLAG \
    --etcd-cluster-join-service=$JUDICATOR \
    --etcd-name=ENV
fi

if [[ $3 != "0" ]]; then
    echo ""
    echo "============================"
    echo "Creating service $EXECUTOR."
    echo "============================"
    echo ""

    docker service create \
    --stop-grace-period=30s \
    --replicas $3 \
    --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
    --network $NETWORK \
    --env NAME={{.Service.Name}}.{{.Task.Slot}} \
    --name $EXECUTOR $KHALA executor \
    --docker-sock=unix:///var/run/docker.sock \
    $EXECUTOR_PRINT_FLAG \
    --etcd-cluster-join-service=$JUDICATOR \
    --etcd-name=ENV \
    --main-name=ENV
fi

echo ""
echo "Wait for $COOL_DOWN_TIME seconds."
sleep $COOL_DOWN_TIME

echo ""
echo "============================"
echo "All Service successfully created."
echo "============================"
echo ""
