```
IP=158.143.102.34

=====

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-init-independent \
--etcd-advertise-address=$IP \
--mongodb-advertise-address=$IP \
--main-advertise-address=$IP \
--etcd-advertise-peer-port=DOCKER \
--etcd-advertise-client-port=DOCKER \
--mongodb-advertise-port=DOCKER \
--main-advertise-port=DOCKER

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$IP:32881 \
--etcd-advertise-address=$IP \
--mongodb-advertise-address=$IP \
--main-advertise-address=$IP  \
--etcd-advertise-peer-port=DOCKER \
--etcd-advertise-client-port=DOCKER \
--mongodb-advertise-port=DOCKER \
--main-advertise-port=DOCKER

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-proxy=on \
--etcd-cluster-join-member-client=http://$IP:32881 \
--etcd-advertise-address=$IP \
--mongodb-advertise-address=$IP \
--main-advertise-address=$IP  \
--etcd-advertise-peer-port=DOCKER \
--etcd-advertise-client-port=DOCKER \
--mongodb-advertise-port=DOCKER \
--main-advertise-port=DOCKER

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 7000 -P khala:v0.1 gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-join-member-client=http://$IP:32881

docker container run -v /var/run/docker.sock:/var/run/docker.sock khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$IP:32881

=====

curl https://discovery.etcd.io/new?size=3

DISCOVERY=https://discovery.etcd.io/91c2dd0f2715e31d42edc44927cad936

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-init-discovery=$DISCOVERY \
--etcd-advertise-address=$IP \
--mongodb-advertise-address=$IP \
--main-advertise-address=$IP \
--etcd-advertise-peer-port=DOCKER \
--etcd-advertise-client-port=DOCKER \
--mongodb-advertise-port=DOCKER \
--main-advertise-port=DOCKER

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 7000 -P khala:v0.1 gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-init-discovery=$DISCOVERY

docker container run -v /var/run/docker.sock:/var/run/docker.sock khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-init-discovery=$DISCOVERY

=====

docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q)

=====

docker network create -d overlay \
--attachable khala

docker service create \
--stop-grace-period=30s \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name judicator-core khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-init-independent \
--etcd-advertise-address=ETH0 \
--mongodb-advertise-address=ETH0 \
--main-advertise-address=ETH0

JOIN_IP=10.0.1.53

docker service create \
--stop-grace-period=30s \
--replicas 4 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name judicator khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001 \
--etcd-advertise-address=ETH0 \
--mongodb-advertise-address=ETH0 \
--main-advertise-address=ETH0

docker service create \
--stop-grace-period=30s \
--replicas 2 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala -p 7000:7000 \
--name gateway khala:v0.1 gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001

docker service scale judicator=2

docker service create \
--stop-grace-period=30s \
--replicas 1 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name executor khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001

docker service scale executor=5

=====

docker service create \
--stop-grace-period=30s \
--replicas 3 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name judicator khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-init-discovery=$DISCOVERY \
--etcd-advertise-address=ETH0 \
--mongodb-advertise-address=ETH0 \
--main-advertise-address=ETH0

=====

docker network create -d overlay \
--attachable khala

docker service create \
--stop-grace-period=30s \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name judicator-core khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-init-independent \
--etcd-advertise-address=DOCKER \
--mongodb-advertise-address=DOCKER \
--main-advertise-address=DOCKER

JOIN_IP=judicator-core.1

docker service create \
--stop-grace-period=30s \
--replicas 2 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name judicator khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001 \
--etcd-advertise-address=DOCKER \
--mongodb-advertise-address=DOCKER \
--main-advertise-address=DOCKER

docker service create \
--stop-grace-period=30s \
--replicas 1 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala -p 7000:7000 \
--name gateway khala:v0.1 gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001

docker service create \
--stop-grace-period=30s \
--replicas 2 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name executor khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001

=====

docker service rm $(docker service ls -q)
```