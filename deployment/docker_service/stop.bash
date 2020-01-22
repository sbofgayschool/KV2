#!/bin/bash

JUDICATOR='judicator'
EXECUTOR='executor'
GATEWAY='gateway'

echo "============================"
echo "Removing all services."
echo "============================"
echo ""

docker service rm $EXECUTOR
docker service rm $GATEWAY
docker service rm $JUDICATOR

echo ""
echo "============================"
echo "All services successfully removed."
echo "============================"
echo ""
