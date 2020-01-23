#!/bin/bash

KHALA='comradestukov/khala:v0.1'

JUDICATOR='judicator'
EXECUTOR='executor'
GATEWAY='gateway'

COOL_DOWN_TIME="25"

if [[ $# != 3 ]]; then
    echo "USAGE: $0 judicator-number gateway-number executor-number"
    exit 1
fi

if [[ $1 = "0" ]]; then
    echo "judicator-number cannot be 0"
    exit 1
fi

echo "============================"
echo "Creating following services:"
echo "$JUDICATOR : $1"
echo "$GATEWAY : $2"
echo "$EXECUTOR : $3"
echo "============================"
echo ""

echo "============================"
echo "Creating first service $JUDICATOR."
echo "============================"
echo ""

docker service create \
--stop-grace-period=30s \
--replicas 1 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--env NAME={{.Service.Name}}.{{.Task.Slot}} \
--name $JUDICATOR $KHALA judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-join-service=$JUDICATOR \
--etcd-advertise-address=DOCKER \
--mongodb-advertise-address=DOCKER \
--main-advertise-address=DOCKER \
--etcd-name=ENV \
--mongodb-name=ENV \
--main-name=ENV

echo "============================"
echo "Scaling service $JUDICATOR to $1."
echo "============================"
echo ""

docker service scale $JUDICATOR=$1

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
    --network khala -p 7000:7000 \
    --env NAME={{.Service.Name}}.{{.Task.Slot}} \
    --name $GATEWAY $KHALA gateway \
    --docker-sock=unix:///var/run/docker.sock \
    --boot-print-log \
    --etcd-print-log \
    --uwsgi-print-log \
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
    --network khala \
    --env NAME={{.Service.Name}}.{{.Task.Slot}} \
    --name $EXECUTOR $KHALA executor \
    --docker-sock=unix:///var/run/docker.sock \
    --boot-print-log \
    --etcd-print-log \
    --main-print-log \
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
