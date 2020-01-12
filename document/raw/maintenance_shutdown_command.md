```
503  bash /Users/chentingyu/Programme/Python/Source/KV2/deployment/init_docker_service.bash 1 5 2 2
504  docker container ls
505  bash /Users/chentingyu/Programme/Python/Source/KV2/deployment/adjust_task_number.bash judicator-core 0 0
506  docker service ls
507  docker service create --stop-grace-period=30s --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock --network khala --name judicator-core khala:v0.1 judicator --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-join-member-client=http://judicator.1.s3a6ha8sdsqd26egmmpvwxxs5:2001 --etcd-advertise-address=DOCKER --mongodb-advertise-address=DOCKER --main-advertise-address=DOCKER
508  bash /Users/chentingyu/Programme/Python/Source/KV2/deployment/adjust_task_number.bash judicator 0 25
509  docker service logs judicator-core 
510  docker service logs gateway
511  docker service logs judicator-core
512  docker container ls
513  docker container exec -it 0ff /bin/bash
514  docker service create --stop-grace-period=30s --replicas $2 --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock --network khala --name $JUDICATOR khala:v0.1 judicator --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-join-member-client=http://judicator-core.1.l0zw2rwe631hxbhvevo5v2d9p:2001 --etcd-advertise-address=DOCKER --mongodb-advertise-address=DOCKER --main-advertise-address=DOCKER
515  docker service create --stop-grace-period=30s --replicas 5 --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock --network khala --name $JUDICATOR khala:v0.1 judicator --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-join-member-client=http://judicator-core.1.l0zw2rwe631hxbhvevo5v2d9p:2001 --etcd-advertise-address=DOCKER --mongodb-advertise-address=DOCKER --main-advertise-address=DOCKER
516  docker service ls
517  docker service create --stop-grace-period=30s --replicas 5 --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock --network khala --name judicator khala:v0.1 judicator --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-join-member-client=http://judicator-core.1.l0zw2rwe631hxbhvevo5v2d9p:2001 --etcd-advertise-address=DOCKER --mongodb-advertise-address=DOCKER --main-advertise-address=DOCKER
518  docker container exec -it 0ff /bin/bash
519  bash /Users/chentingyu/Programme/Python/Source/KV2/deployment/adjust_task_number.bash judicator-core 0 0
520  docker service create --stop-grace-period=30s --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock --network khala --name judicator-core khala:v0.1 judicator --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-join-member-client=http://judicator.1.ultwqdirhnq1sm5esonlyjsnf:2001 --etcd-advertise-address=DOCKER --mongodb-advertise-address=DOCKER --main-advertise-address=DOCKER
521  bash /Users/chentingyu/Programme/Python/Source/KV2/deployment/adjust_task_number.bash judicator 0 30
522  docker service rm judicator-core judicator gateway executor
```