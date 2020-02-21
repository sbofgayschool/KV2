#### Boot
```
run:
    load_args(boot)
    FOR s IN services:
        load_args(s)
    parse_args()
    config = load_config(boot)
    FOR s IN services:
        write_config(s)
    LOOP UNTIL SIGINT:
        FOR s IN services:
            lock(s.pid_file)
            IF NOT s.process.running:
                s.process = subprocess.run(s)
                s.pid_file.write(s.process.pid)
            unlock(s.pid_file)
        sleep(interval)
    FOR s IN services:
        s.process.kill()
        s.process.join()
    RETURN
```

#### Etcd
```
check:
    sleep(interval)
    IF NOT etcd_process.working:
        etcd_process.kill()
    RETURN

run:
    config = load_config(etcd)
    IF config.cluster:
        IF config.cluster.service:
            joining_nodes = docker.service.find(config.cluster.service)
            IF NOT joining_nodes:
                config.cluster.type = "init"
            ELSE:
                config.cluster.type = "join"
                config.cluster.client = choose_one(joining_nodes)
        IF config.cluster.type == "join" and NOT config.cluster.member:
            IF NOT config.proxy:
                remote_etcd = etcd_proxy(config.cluster.client)
                remote_etcd.add_member(config.address)
            config.cluster.member = remote_etcd.get_member()
    etcd_process = subprocess.run(config)
    check_thread = thread.run(check)
    LOOP UNTIL SIGINT OR EOF:
        log_output(etcd_process)
    etcd_process.kill()
    etcd_process.join()
    IF NOT config.proxy:
        local_etcd.remove_member(config.address)
    RETURN
```

#### Mongodb
```
global working = TRUE

register:
    sleep(interval)
    IF NOT mongodb_process.working:
        mongodb_process.kill()
        RETURN
    IF local_etcd.insert(init_key, config.address):
        local_mongodb.init_replica_set()
    local_etcd.set(reg_key, config.address)
    WHILE working:
        sleep(interval)
        IF local_mongodb.is_primary():
            registered_member = local_etcd.get_list(reg_key)
            replica_set_member = local_mongodb.get_member()
            local_mongodb.remove_member(replica_set_membger - registered_member)
            local_mongodb.add_member(registered_member - replica_set_member)
    RETURN

run:
    config = load_config(mongodb)
    mongodb_process = subprocess.run(config)
    register_thread = thread.run(register)
    LOOP UNTIL SIGINT OR EOF:
        log_output(mongodb_process)
    working = FALSE
    register_thread.join()
    mongodb_process.kill()
    mongodb_process.join()
    local_etcd.delete(reg_key, config.address)
    RETURN
```

#### Uwsgi
```
run:
    config = load_config(mongodb)
    write_ini_config(config)
    uwsgi_process = subprocess.run(config)
    LOOP UNTIL SIGINT OR EOF:
        log_output(uwsgi_process)
    uwsgi_process.kill()
    uwsgi_process.join()
    RETURN
```

#### Judicator Main
```
```

#### Executor Main
```
```

#### Gateway Server
```
```
