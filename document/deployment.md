# Deployment

This page briefly introduces how the system can be deployed.

**It is suggested that you should deploy at least three Judicators, to make use of the high availability of the 
system.**

*This system is mainly designed to be working in docker containerized environment. You can still make it work
without docker environment, but may have experience the best performance.*

*This page supposes that your OS is an UNIX-like system. If you are working with a Windows system, please
change the commands into the corresponding Windows CMD/powershell/terminal ones.*

*For full arguments document, please see [document/arguments.md](arguments.md).*

## Direct Deployment

The system can be directly deployed without docker.

#### Dependency

- Python3
- pip
- virtualenv
- Etcd
- MongoDB
- uwsgi

#### Install

Clone the repository directly.

```bash
git clone https://github.com/ComradeStukov/KV2
cd KV2
virtualenv --no-site-packages venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
deactivate
```

#### Start up

You can simply start one of the node inside the repository. Here is an example of running a Judicator node.

```bash
source venv/bin/activate
cd judicator
bash clean.bash
python3 boot.py --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-init-independent
```

You can also use different work directories to start multiple instance.

*It is required that there **MUST** be a **config** directory with config templates stored inside its subdirectory
**templates** exists in the directory where the start up command is executed. (this is due to a design defect that the
path to config templates can not be configured, and it might be improved in the future)*

```bash
cd PATH_TO_ANOTHER_DIR
cp -R PATH_TO_KHALA_REPOSITORY/judicator/config ./config
cp PATH_TO_KHALA_REPOSITORY/judicator/clean.bash ./clean.bash
bash clean.bash
source PATH_TO_KHALA_REPOSITORY/venv/bin/activate
```

Then you have to edit the exe and other related fields in all configuration template according to
the real path to python scripts inside Khala repository.

For example, the line 2 in config/templates/main.json should be edited:

"exe": ["python3", "main.py"] ----> "exe": ["python3", "PATH_TO_KHALA_REPOSITORY/judicator/main.py"]

you can then start up the node.

```bash
export PYTHONPATH=PATH_TO_KHALA_REPOSITORY
python3 PATH_TO_KHALA_REPOSITORY/judicator/boot.py --boot-print-log --etcd-print-log --mongodb-print-log --main-print-log --etcd-cluster-init-independent
```

You may wish to run clean.bash before start up to remove runtime generated files of last execution and 
(re)create necessary working directories.

Also, you can put Etcd and MongoDB startup files in data/etcd_init and data/mongodb_init. These files will be copied
to Etcd and MongoDB data directories before starting them up.

Use kill -INT to stop the running node.

## Single Docker Container

Use docker image from [docker hub](https://hub.docker.com/repository/docker/comradestukov/khala) to run nodes in
containers is far simpler.

#### Dependency

- Docker

#### Install

Pull the docker image.

```bash
KHALA='comradestukov/khala:v0.1'
docker pull $KHALA
```

#### Start up

Set the bash variable IP to an exposed address of the host. It can not be localhost, as it must be accessible inside a docker container.

A judicator can be startup with the following command.

```bash
IP=EXPOSED_IP
KHALA='comradestukov/khala:v0.1'
docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P $KHALA judicator \
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
```

Use the following command to check the exposed port mapped to 2001 (Etcd client) of the started up container.

```bash
docker container ls -a
```

Similarly, you can also start a Gateway.

```bash
IP=EXPOSED_IP
KHALA='comradestukov/khala:v0.1'
docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 7000 -P $KHALA gateway \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--uwsgi-print-log \
--etcd-cluster-join-member-client=http://$IP:EXPOSED_PORT_TO_PORT_2001_OF_A_JUDICATOR
```

An Executor can then be started up.

```bash
IP=EXPOSED_IP
KHALA='comradestukov/khala:v0.1'
docker container run -v /var/run/docker.sock:/var/run/docker.sock $KHALA executor \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$IP:EXPOSED_PORT_TO_PORT_2001_OF_A_JUDICATOR
```

You can visit the website held by the Gateway through http://localhost:EXPOSED_PORT_TO_PORT_7000_OF_A_GATEWAY.

More Executors and Gateways can be started up by the same command. However, if you want to start up more Judicators,
the following commands should be used.

```bash
IP=EXPOSED_IP
KHALA='comradestukov/khala:v0.1'
docker container run -v /var/run/docker.sock:/var/run/docker.sock \
--expose 2000 \
--expose 2001 \
--expose 3000 \
--expose 4000 -P $KHALA judicator \
--docker-sock=unix:///var/run/docker.sock \
--boot-print-log \
--etcd-print-log \
--mongodb-print-log \
--main-print-log \
--etcd-cluster-join-member-client=http://$IP:EXPOSED_PORT_TO_PORT_2001_OF_A_JUDICATOR \
--etcd-advertise-address=$IP \
--mongodb-advertise-address=$IP \
--main-advertise-address=$IP  \
--etcd-advertise-peer-port=DOCKER \
--etcd-advertise-client-port=DOCKER \
--mongodb-advertise-port=DOCKER \
--main-advertise-port=DOCKER
```

Use docker cp or mount to copy configuration template and initialize data files into the containers.
You may also wish to use this method to put custom tools and configurations into the containers (especially Executors).

Use Ctrl-C or docker container stop with timeout of 30s to stop a container. Do not use docker container kill unless 
necessary, for a killed container will not clean up upon exiting.

## Docker Swarm (Docker Service) - RECOMMENDED

The system is designed to work with docker swarm clusters.

#### Dependency

- docker
- Python

#### Install Ansible (not required if Ansible is installed or docker swarm has been configured)

```bash
git clone https://github.com/ComradeStukov/KV2
cd KV2/deployment/ansible
bash install.bash
```

#### Config Ansible, Install Docker and Config Docker Swarm (not required if docker swarm has been configured)

Config the host group of Ansible. If the docker is install by the install.bash provided, the host configuration should
be found at ~/.ansible/hosts.

Add two groups: **khala_manager** (manager nodes in docker swarm) and **khala_worker** (worker
nodes in docker swarm). Note, the localhost must be in khala_manager group. You may wish to configure other connection
parameters in the file.

Ansible use ssh to login to target hosts and carry out commands. Please upload the ssh public key of current user
on local machine to target user account in remote machines.

Then the docker installation and docker swarm configuration can be done by one command. 
Run the Ansible playbook use a user with sudo privilege in all target hosts.

If all target hosts share a common user with same password, use the following command.

```bash
USER=THE_USER
PASSWORD=THE_PASSWORD_OF_THE_USER_ON_TARGET_HOSTS
cd KV2/deployment/ansible
ansible-playbook -u $USER --extra-vars "ansible_become_pass=$PASSWORD" install_docker.yml
```

You may wish to store the password in the install_docker_passwd.yml, and use the following command.

```bash
USER=THE_USER
cd KV2/deployment/ansible
ansible-playbook -u $USER --extra-vars "@install_docker_passwd.yml" install_docker.yml
```

Moreover, you can encrypt the file with vault, and use the following command.

```bash
USER=THE_USER
cd KV2/deployment/ansible
ansible-playbook -u $USER --ask-vault-pass --extra-vars "@install_docker_passwd.yml" install_docker.yml
```

#### Start up

Simply start the cluster using provided script. If you would like to start a cluster with 3 Judicators, 1 Gateway and 
1 Executor, just use the following command.

```bash
cd KV2/deployment/docker_service
bash start.bash 3 1 1 --output-log
```

You can visit http://localhost:7000 to see the website of the cluster after the deployment.

**Using docker service shares something same with using single docker container. Reference to each other when needed.**
