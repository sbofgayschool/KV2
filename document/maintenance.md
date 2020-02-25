# Maintenance

This page briefly describes how to maintain the system.

*This page supposes that your OS is an UNIX-like system or in docker container. If you are working with a Windows
system, please change the commands into the corresponding Windows CMD/powershell/terminal ones.*

## Availability and Scalability

The system is designed to be robust with high availability. It can tolerates minor member (less than half of the total
member) failures. It is also able to be scaled up and down while it is running to reach a balance of consumed resources 
and performance. With docker swarm, the system can provide the best performance.

Nevertheless, though the system has the potentiality to have features of automatic scaling and load balancing,
yet they have not been developed yet. It may be improved later.

## Scaling

When running without docker or in single container mode, scaling can be achieved by simply running commands used for 
starting up or stop a node. See [deployment.md](deployment.md) for details.

When running in docker swarm environment, use the given script reconfig_tasks.bash to scale the system, and stop.bash
to stop the system.

For example, if you want to config the number of Judicators to 5 with interval of 30s between starting up each new
nodes, you can simply use the following command.

```bash
cd KV2/deployment/docker_service
bash reconfig_tasks.bash judicator 5 30
```

**When reducing the number of a kind of nodes through reconfiguration, the interval (third parameter) should at least 
be 25, to ensure a stable status of the system.**

If you want to stop the whole system, use the following command.

```bash
cd KV2/deployment/docker_service
bash stop.bash
```

## Maintenance

All nodes can be maintained in run time. However, as most maintenance involves temporarily shutting down some modules 
inside the node, some pre-actions should be taken.

The boot program will regularly check all modules and restart them regularly. In order to force it to skip checking
specified modules, the corresponding pid files should be locked. This can be achieved by using the maintain.py script
provided. The script will lock given pid files (thus boot program will temporarily skip checking those modules), and 
then open a shell inside it. It will release the lock when that shell is closed.

You will be able to carry out maintenance inside the shell opened by the maintain.py script.

When running in docker container, you have to enter a running container. You can used the following command to do this.

```bash
docker container exec -it CONTAINER_ID /bin/bash
```

Here are two examples of maintain a node in runtime.

#### Modify configurations for main program in Judicator

- Use maintain.py to lock corresponding pid files and open a shell. This can be done by following commands.

```bash
cd KV2
python3 maintain.py judicator/data/main.pid
```

- Stop the main module by kill -INT, as prompted when opening the maintenance script. Wait for main module to exit,
and use ps -ef to check. If it is still running after one minute, kill it again (This should not happen, but if it does
, do it).
- Edit judicator/config/main.json as you wish.
- Exit the shell.

#### Disaster Recovery

- Stop all Executors and Gateways. Shutdown all but one Judicator nodes.
- Use maintain.py to lock all pid files

```bash
cd KV2
python3 maintain.py judicator/data/main.pid judicator/data/mongodb.pid judicator/data/etcd.pid
```

- Stop all modules by kill -INT, as prompted when opening the maintenance script. Wait for them to exit,
and use ps -ef to check. If some of them are still running after one minute, kill them again (This should not happen,
but if it does, do it).
- Copy files from backup or from current data directory of the MongoDB at judicator/data/mongodb to
judicator/data/mongodb_init.
- Backup the Etcd config file at judicator/config/etcd.json.
- Edit the Etcd config file, modify the cluster field to:

```
{
    ...
    "etcd": {
        ...
        "cluster": {
            "type": "init"
        }
        ...
    }
    ...
}
```

- Exit the shell. Wait for all modules to work stably.
- Use the backup Etcd config file to overwrite the current one.
- Clean judicator/data/mongodb_init.
- Reconfig the system to a proper size.

## Logs

The logs are stored in log directory of every modules in default.

If --module-print-log is specified, then the log of corresponding module will be output to stdout stream. If it 
runs in docker environment, then docker logs or docker service logs commands can be used to fetch it.

## Backup

System backup actually only involves backing up MongoDB database. You can use docker cp and operations provided by 
[MongoDB](https://docs.mongodb.com/manual/core/backups/) to backup and restore MongoDB system.

*There is currently no method to backup an Executor, especially the task they are executing. This may be improved in
the future.*

## Update

Rolling update can be applied manually when running without docker and in single docker container, or by
[rolling update](https://docs.docker.com/engine/swarm/swarm-tutorial/rolling-update/) mechanism provided by 
docker swarm when the system in running in docker swarm.
