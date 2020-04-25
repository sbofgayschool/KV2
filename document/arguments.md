# Arguments

This page describes command line arguments which can be used to config the node upon start up.

All the arguments are optional.

Upon start up, the Boot program will load config templates (in config/template), and update it with input arguments.
It than writes updated configuration to config files (in config/). The config file will be loaded by other components
later when boot (re)start them.

*Not all configuration can be changed by arguments by now (this is due to a design defect and might be improved
in the future).*

## Common Arguments

#### Boot

| flag | meaning | type | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: |
| --docker-sock | Path to mapped docker sock file | string | null | | --docker-sock=unix:///var/run/docker.sock |
| --retry-times | Total retry time of key operations | int | 3 | | --retry-times=3 |
| --retry-interval | Interval between retries of key operations | int | 5 | | --retry-interval=5 |
| --boot-check-interval | Interval between services check in boot module | int | 30 | | --boot-check-interval=30 |
| --boot-print-log | Print the log of boot module to stdout | bool | false | | --boot-print-log |

#### Etcd

| flag | meaning | type | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: |
| --etcd-exe | Path to etcd executable file | string | etcd | will be etcd when --docker-sock is specified | --etcd-exe=./etcd |
| --etcd-name | Name of the etcd node | string | etcd | from environment variable NAME if it is ENV, and will be hostname if it is null and --docker-sock is specified | --etcd-name=etcd |
| --etcd-proxy | If etcd node should be in proxy mode | string | null for Judicator, on for Executor and Gateway | | --etcd-proxy=on |
| --etcd-strict-reconfig | If the etcd should be in strict reconfig mode | bool | false | | --etcd-strict-reconfig |
| --etcd-listen-peer-port | Listen peer port of the etcd node | int | 2000 for Judicator, 5000 for Executor, 6000 for Gateway | | --etcd-listen-peer-port=2000 |
| --etcd-listen-client-port | Listen client port of the etcd node | int | 2001 for Judicator, 5001 for Executor, 6001 for Gateway | | --etcd-listen-client-port=2001 |
| --etcd-advertise-peer-port | Advertise peer port of the etcd node | int or DOCKER | 2000 for Judicator, 5000 for Executor, 6000 for Gateway | get exposed docker port if it is DOCKER | --etcd-advertise-peer-port=2000 |
| --etcd-advertise-client-port | Advertise client port of the etcd node | int or DOCKER | 2001 for Judicator, 5001 for Executor, 6001 for Gateway | get exposed docker port if it is DOCKER | --etcd-advertise-client-port=2001 |
| --etcd-cluster-init-discovery | Discovery token url of etcd node | string | null | | --etcd-cluster-init-discovery=url |
| --etcd-cluster-join-member-client | Client url of a member of the cluster which this etcd node is going to join | string | null | override above cluster config | --etcd-cluster-join-member-client=http://localhost:2001 |
| --etcd-cluster-service | Service name if the etcd is going to use docker swarm and dns to auto detect members | string | null | override above cluster config | --etcd-cluster-service=judicator |
| --etcd-cluster-service-port | Etcd client port used for auto detection, default is 2001 | int | 2001 | should be used with --etcd-cluster-service | --etcd-cluster-service-port=2001 |
| --etcd-print-log | Print the log of etcd module to stdout | bool | false | | --etcd-print-log |

## Judicator

#### Etcd

| flag | meaning | type | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: |
| --etcd-listen-address | Listen address of the etcd node | string | 0.0.0.0 | DOCKER for full container name, NI name in upper letters for address of that NI | --etcd-listen-address=0.0.0.0 |
| --etcd-advertise-address | Advertise address of the etcd node | string | localhost | DOCKER for full container name, NI name in upper letters for address of that NI | --etcd-advertise-address=localhost |
| --etcd-cluster-init-member | Name-url pairs used for initialized of etcd node | string | null | override --etcd-cluster-init-discovery | --etcd-cluster-init-member="etcd1=http://localhost:2000" |
| --etcd-cluster-init-independent | If the etcd node is going to be the only member of the cluster | true | override --etcd-cluster-init-discovery and --etcd-cluster-init-member | | --etcd-cluster-init-independent |

#### MongoDB

| flag | meaning | type | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: |
| --mongodb-exe | Path to mongodb executable file | string | mongod | will be mongod when --docker-sock is specified | --mongodb-exe=./mongod |
| --mongodb-name | Name of the mongodb node | string | mongdb | from environment variable NAME if it is ENV, and will be hostname if it is null and --docker-sock is specified | --mongodb-name=mongodb |
| --mongodb-listen-address | Listen address of the mongodb node | string | 0.0.0.0 | DOCKER for full container name, NI name in upper letters for address of that NI | --mongodb-listen-address=0.0.0.0 |
| --mongodb-listen-port | Listen port of the etcd node | int | 3000 | | --mongodb-listen-port=3000 |
| --mongodb-advertise-address | Advertise address of the mongodb node | string | localhost | DOCKER for full container name, NI name in upper letters for address of that NI | --mongodb-advertise-address=localhost |
| --mongodb-advertise-port | Advertise port of the etcd node | 3000 | int or DOCKER | get exposed docker port if it is DOCKER | --mongodb-advertise-port=3000 |
| --mongodb-replica-set | Name of the replica set which the mongodb node is going to join | string | rs | | --mongodb-replica-set=rs |
| --mongodb-print-log | Print the log of mongodb module to stdout | bool | false | | --mongodb-print-log |

#### Judicator Main

| flag | meaning | type | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: |
| --main-name | Name of the judicator | string | judicator | from environment variable NAME if it is ENV, and will be hostname if it is null and --docker-sock is specified | --main-name=judicator |
| --main-listen-address | Listen address of judicator rpc service | string | 0.0.0.0 | DOCKER for full container name, NI name in upper letters for address of that NI | --main-listen-address=0.0.0.0 |
| --main-listen-port | Listen port of judicator rpc service | int | 4000 | | --main-listen-port=4000 |
| --main-advertise-address | Advertise address of judicator rpc service | string | localhost | DOCKER for full container name, NI name in upper letters for address of that NI | --main-advertise-address=localhost |
| --main-advertise-port | Advertise port of judicator rpc service | int or DOCKER | 4000 | get exposed docker port if it is DOCKER | --main-advertise-port=4000 |
| --main-print-log | Print the log of main module to stdout | bool | false | | --main-print-log |

## Executor

#### Executor Main

| flag | meaning | type | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: |
| --main-name | Name of the executor | string | executor | from environment variable NAME if it is ENV, and will be hostname if it is null and --docker-sock is specified | --main-name=executor |
| --main-task-vacant | Capacity of tasks of the executor | int | 3 | | --main-task-vacant=3 |
| --main-report-interval | Interval between reports made to judicator from executor | int | 5 | | --main-report-interval=5 |
| --main-task-user-group | User:group string indicating execution user/group when executing real tasks | string | current user and current group | executor:executor (auto created) will be used when --docker-sock is specified | --main-task-user-group=user:group |
| --main-print-log | Print the log of main module to stdout | bool | false | | --main-print-log |

## Gateway

#### Uwsgi

| flag | meaning | type | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: |
| --uwsgi-host | Listen address of uwsgi | string | 0.0.0.0 | DOCKER for full container name, NI name in upper letters for address of that NI | --uwsgi-host=0.0.0.0 |
| --uwsgi-port | Listen port of uwsgi | int | 7000 | | --uwsgi-port=7000 |
| --uwsgi-processes | Number of process of the uwsgi | int | 4 | | --uwsgi-processes=3 |
| --uwsgi-threads | Number of thread in each the uwsgi process | int | 2 | | --uwsgi-threads=2 |
| --uwsgi-print-log | Print the log of uwsgi module to stdout | bool | false | | --uwsgi-print-log |
