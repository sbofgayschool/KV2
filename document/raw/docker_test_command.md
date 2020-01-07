```
docker container run -v /var/run/docker.sock:/var/run/docker.sock --expose 2000 --expose 2001 --expose 3000 --expose 4000 -P khala:v0.1 judicator --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-init-independent --etcd-advertise-address=158.143.101.109 --mongodb-advertise-address=158.143.101.109 --main-advertise-address=158.143.101.109

docker container run -v /var/run/docker.sock:/var/run/docker.sock --expose 2000 --expose 2001 --expose 3000 --expose 4000 -P khala:v0.1 judicator --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-join-member-client=http://158.143.101.109:32829 --etcd-advertise-address=158.143.101.109 --mongodb-advertise-address=158.143.101.109 --main-advertise-address=158.143.101.109

docker container run -v /var/run/docker.sock:/var/run/docker.sock --expose 6000 --expose 6001 --expose 7000 -P khala:v0.1 gateway --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --uwsgi-print-log --etcd-cluster-join-member="f588d27bd229=http://158.143.101.109:32830" --etcd-advertise-address=158.143.101.109

docker container run -v /var/run/docker.sock:/var/run/docker.sock --expose 5000 --expose 5001 -P khala:v0.1 executor --docker-sock=unix:///var/run/docker.sock --boot-print-log --etcd-print-log --main-print-log --etcd-cluster-join-member="f588d27bd229=http://158.143.101.109:32830" --etcd-advertise-address=158.143.101.109

docker kill $(docker ps -a -q) && docker rm $(docker ps -a -q)
```