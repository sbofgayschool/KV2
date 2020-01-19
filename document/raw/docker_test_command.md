#### Single container IP
```
IP=158.143.100.251

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P comradestukov/khala:v0.1 judicator \
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
--expose 4000 -P comradestukov/khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$IP:32786 \
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
--expose 4000 -P comradestukov/khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-proxy=on \
--etcd-cluster-join-member-client=http://$IP:32831 \
--etcd-advertise-address=$IP \
--mongodb-advertise-address=$IP \
--main-advertise-address=$IP  \
--etcd-advertise-peer-port=DOCKER \
--etcd-advertise-client-port=DOCKER \
--mongodb-advertise-port=DOCKER \
--main-advertise-port=DOCKER

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 7000 -P comradestukov/khala:v0.1 gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-join-member-client=http://$IP:32831

docker container run -v /var/run/docker.sock:/var/run/docker.sock comradestukov/khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$IP:32831
```

#### Single container discovery
```
curl https://discovery.etcd.io/new?size=3

DISCOVERY=https://discovery.etcd.io/91c2dd0f2715e31d42edc44927cad936

docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P comradestukov/khala:v0.1 judicator \
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
--expose 7000 -P comradestukov/khala:v0.1 gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-init-discovery=$DISCOVERY

docker container run -v /var/run/docker.sock:/var/run/docker.sock comradestukov/khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-init-discovery=$DISCOVERY
```

#### Stop all containers
```
docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q)
```

#### Service IP
```
docker network create -d overlay \
--attachable khala

docker service create \
--stop-grace-period=30s \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name judicator-core comradestukov/khala:v0.1 judicator \
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
--name judicator comradestukov/khala:v0.1 judicator \
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
--name gateway comradestukov/khala:v0.1 gateway \
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
--name executor comradestukov/khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001

docker service scale executor=5
```

#### Service Discovery
```
docker service create \
--stop-grace-period=30s \
--replicas 3 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--name judicator comradestukov/khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-init-discovery=$DISCOVERY \
--etcd-advertise-address=ETH0 \
--mongodb-advertise-address=ETH0 \
--main-advertise-address=ETH0
```

#### Service DNS
```
docker network create -d overlay \
--attachable khala

docker service create \
--stop-grace-period=30s \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--env NAME={{.Service.Name}}-{{.Task.Slot}} \
--name judicator-core comradestukov/khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-init-independent \
--etcd-advertise-address=DOCKER \
--mongodb-advertise-address=DOCKER \
--main-advertise-address=DOCKER \
--etcd-name=ENV \
--mongodb-name=ENV \
--main-name=ENV

JOIN_IP=judicator-core.1.ms7bq7fwolgavya2llvhjgsnv

docker service create \
--stop-grace-period=30s \
--replicas 1 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--env NAME={{.Service.Name}}-{{.Task.Slot}} \
--name judicator comradestukov/khala:v0.1 judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001 \
--etcd-advertise-address=DOCKER \
--mongodb-advertise-address=DOCKER \
--main-advertise-address=DOCKER \
--etcd-name=ENV \
--mongodb-name=ENV \
--main-name=ENV

docker service create \
--stop-grace-period=30s \
--replicas 1 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala -p 7000:7000 \
--env NAME={{.Service.Name}}-{{.Task.Slot}} \
--name gateway comradestukov/khala:v0.1 gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001 \
--etcd-name=ENV

docker service create \
--stop-grace-period=30s \
--replicas 2 \
--mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
--network khala \
--env NAME={{.Service.Name}}-{{.Task.Slot}} \
--name executor comradestukov/khala:v0.1 executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$JOIN_IP:2001 \
--etcd-name=ENV \
--main-name=ENV
```

#### Service remove all
```
docker service rm $(docker service ls -q)
```

#### Ansible install docker
```
Ref: https://www.cnblogs.com/sparkdev/p/9962904.html
Ref: https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html

ansible-playbook -u chenty --ask-vault-pass --extra-vars '@~/.ansible/vault/doc_vm_passwd.yml' pb_docker.yml

ansible-playbook -u chenty --extra-vars '@install_docker_passwd.yml' install_docker.yml

ansible-playbook -u chenty --extra-vars "password=your_password" install_docker.yml
```