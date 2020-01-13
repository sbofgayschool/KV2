## Short Term
- Figure out how Ansible playbook can help when installing docker on remote computer.
- Write a one-shot script to install the whole thing,
including docker (on both local and remote computer), docker service initialize, cluster initialize, etc.
- Add full documents, majorly about usage and maintenance, but also should also have something about source code.
- Thorough check and necessary tests.
- Build and upload the v0.1 image on docker host.

#### Finished / Canceled:
- Add file size check for both gateway and executor when encountering too large task files.
- Add exception handler after insert/update mongodb on judicator to prevent write failure when writing large files.
- <b>NOT POSSIBLE</b> <del>Figure out if it is possible to limit the disk space of the docker container.</del>
- Add RPC input validation for judicator.
- Add form validation for gateway, both backend and frontend.
- Add comments on webpage javascript.
- Add argument helper string in all boot.py.
- Add **/test to .dockerignore.

## Long Term
- <b>Security issue:</b> Find out a way to completely isolate all single tasks
OR
set a full limitation (CPU, memory, disk space, etc.) on all single tasks.
- Add user functions (user register, login, etc.) and admin functions.
- Make restart of a killed, randomly port-mapped docker container available.
- Internationalize.
- Windows OS support in un-docker environment.
- Authentication in RPC calls in all RPC interfaces.
- Avoid all hard-coded IP address.
- Better use of docker DNS, and get rid of container-id. Finally allows changing IP of a node in runtime.
- Add new nodes to the system even when the system has failed nodes.

#### Finished / Canceled:
- None