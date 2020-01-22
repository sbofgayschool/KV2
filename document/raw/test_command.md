#### Etcd
```
Ref: https://github.com/etcd-io/etcd/blob/master/Documentation/v2/clustering.md

./etcd --name infra1 \
--data-dir=infra1 \
--initial-advertise-peer-urls http://127.0.0.1:2001 \
--listen-peer-urls http://127.0.0.1:2001 \
--listen-client-urls http://127.0.0.1:3001 \
--advertise-client-urls http://127.0.0.1:3001 \
--initial-cluster-state existing \
--initial-cluster infra0=http://127.0.0.1:2000,infra1=http://127.0.0.1:2001

--discovery https://discovery.etcd.io/0e68979d91ab35df817f5c32b9c14b12

curl http://127.0.0.1:3000/v2/members -XPOST \
-H "Content-Type: application/json" -d '{"peerURLs":["http://127.0.0.1:2001"]}'

curl http://127.0.0.1:3000/v2/members -XGET

./etcd --name infra0 \
--data-dir=infra0 \
--initial-advertise-peer-urls http://127.0.0.1:2000 \
--listen-peer-urls http://127.0.0.1:2000 \
--listen-client-urls http://127.0.0.1:3000 \
--advertise-client-urls http://127.0.0.1:3000 \
--initial-cluster-state new \
--initial-cluster infra0=http://127.0.0.1:2000

./etcd --name infra2 \
--proxy on \
--data-dir=infra2 \
--initial-advertise-peer-urls http://127.0.0.1:2002 \
--listen-peer-urls http://127.0.0.1:2002 \
--listen-client-urls http://127.0.0.1:3002 \
--advertise-client-urls http://127.0.0.1:3002 \
--initial-cluster-state existing \
--initial-cluster infra0=http://127.0.0.1:2000
```

#### MongoDB
```
Ref: https://docs.mongodb.com/manual/administration/replica-set-deployment/

mongod --replSet "rs0" --bind_ip localhost --port 7000 --dbpath /Users/chentingyu/Programme/Practice/MongoDB/store0

rs.initiate( {
   _id : "rs0",
   members: [
      { _id: 0, host: "127.0.0.1:7000" }
   ]
})

rs.add( { host: "127.0.0.1:7001", priority: 1, votes: 1 } )

rs.add( { host: "127.0.0.1:7002", priority: 1, votes: 1 } )

mongod --replSet "rs0" --bind_ip localhost --port 7001 --dbpath /Users/chentingyu/Programme/Practice/MongoDB/store1

mongod --replSet "rs0" --bind_ip localhost --port 7002 --dbpath /Users/chentingyu/Programme/Practice/MongoDB/store2
```

#### Clear iptables
```
Ref: https://www.digitalocean.com/community/tutorials/how-to-list-and-delete-iptables-firewall-rules

sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT ACCEPT
sudo iptables -t nat -F
sudo iptables -t mangle -F
sudo iptables -F
sudo iptables -X

sudo apt-get -y remove fail2ban ufw
sudo apt-get -y purge fail2ban ufw
sudo apt-get -y autoremove
```