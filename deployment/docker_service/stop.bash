#!/bin/bash

JUDICATOR_CORE='judicator-core'
JUDICATOR='judicator'
EXECUTOR='executor'
GATEWAY='gateway'

docker service rm $EXECUTOR
docker service rm $GATEWAY
docker service rm $JUDICATOR
docker service rm $JUDICATOR_CORE

echo "==========================="
echo "All services removed."
echo "==========================="
echo ""