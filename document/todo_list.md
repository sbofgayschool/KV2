# Todo list

This page contains todo list for the whole project.

## Short Term

- None.

#### Finished / Canceled:

- Add file size check for both gateway and executor when encountering too large task files.
- Add exception handler after insert/update mongodb on judicator to prevent write failure when writing large files.
- <b>NOT POSSIBLE</b> <del>Figure out if it is possible to limit the disk space of the docker container.</del>
- Add RPC input validation for judicator.
- Add form validation for gateway, both backend and frontend.
- Add comments on web page javascript.
- Add argument helper string in all boot.py.
- Add an argument indicating if the name can be get from the environment variable name.
- When adding a member to etcd cluster, check if a previous member with same name exists.
- Add registration of mongodb name-address pair on etcd, and remove exit mechanism.
- Modify mongodb deletion mechanism to deleting all nodes exist in replica set but are not registered.
- Check whether the registered value is correct before unregistering main, mongodb and etcd of judicator.
- Figure out how Ansible playbook can help when installing docker on remote computer.
This can be tested on VM of DoC IC.
- Write one-shot scripts to install the whole thing,
including docker (on both local and remote computer), docker service initialize, cluster initialize, etc.
- Formalize logs.
- Remove warning from thrift generation.
- Necessary tests on VM of Doc IC.
- More strict check on input.
- Make maintain.py be able to lock multiple pid files.
- <b>CANCELED, shellx.doc.ic.ac.uk does not open any possible ports due to the configuration of its iptables 
(or something else) .</b> <del>A python based proxy for Khala on VM of Doc IC (Small Independent Project).</del>
- Add full tests:
etcd_proxy, etcd_daemon, mongodb_proxy, mongodb_daemon, uwsgi_daemon, boot_daemon (with uwsgi), system (integrated).
- Add regular refresh to web pages.
- Add full documents, majorly about usage and maintenance, but also should also have something about source code.
- Build and upload formal v0.1 image on docker host.

## Long Term

- <b>Security issue:</b> Find out a way to completely isolate all single tasks
OR
set a full limitation (CPU, memory, disk space, etc.) on all single tasks.
- Add user functions (user register, login, etc.) and admin functions.
- Internationalize.
- Windows OS support in un-docker environment.
- Authentication in RPC calls for all RPC interfaces.
- Make all parameters, especially including paths to configurations, configurable in command line
(at least paths to config templates, config files, data directories, pid files and all runtime used files),
so multiple instances can be run using only one executable scripts without docker environment.

#### Finished / Canceled:

- Avoid all hard-coded IP address.
- Better use of docker DNS, and get rid of container-id.
- Add new nodes to the system even when the system has failed nodes.
- Make restart of a killed, randomly port-mapped docker container available.
- Refactor codes to avoid duplication, especially in boot.py and etcd_daemon.py
