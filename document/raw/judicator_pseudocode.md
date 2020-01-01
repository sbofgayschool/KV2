#### Ectd daemon
```
IF etcd.dir exists:
    run this.etcd
ELSE:
    IF initializing:
        run this.etcd --initialize
    ELSE:
        remote.etcd.add(this.etcd)
        members = remote.etcd.member
        run this.etcd --join members=members
check_thread = Thread(Check)
check_thread.set_daemon()
check_thread.run()
log(this.etcd.output) UNTIL EOF

Check:
    WHILE try_time > 0:
        sleep(few_seconds)
        IF this.etcd.serving():
            BREAK
        try_time = try_time - 1
    IF try_time == 0:
        this.etcd.kill()
```

#### MongoDB daemon
```
run this.mongodb
register_thread = Thread(Register)
register_thread.set_daemon()
register_thread.run()
log(this.mongodb.output) UNTIL EOF

Register:
    WHILE try_time > 0:
        sleep(few_seconds)
        IF this.mongodb.serving():
            BREAK
        try_time = try_time - 1
    IF try_time == 0:
        this.mongodb.kill()
        END
    this.etcd.mongodb/primary.set_if_empty(this.mongodb)
    IF this.etcd.mongodb/primary == this.mongodb:
        this.mongodb.intialize_rs
    ELSE:
        remote.mongodb = this.etcd.mongodb/primary
        IF NOT this.mongodb IN remote.mongodb.member_list:
            IF remote.mongodb.vote_member < 7:
                remote.mongodb.add(this.mongodb, vote, priority)
            ELSE:
                remote.mongodb.add(this.mongodb)
    WHILE true:
        IF this.mongodb.primary_member == this.mongodb:
            this.etcd.mongodb/primary.set(this.mongodb)
        sleep(duration)
```

#### Main
```
lead_thread = Thread(Register)
lead_thread.set_daemon()
lead_thread.run()
register_thread = Thread(Register)
register_thread.set_daemon()
register_thread.run()
start_rpc_server(Add, Cancel, Search, Get, Report)

Lead():
    WHILE true:
        sleep(duration)
        success = this.etcd.judicator/leader.set_if_empty(this.name, ttl=ttl)
        IF success == false:
            success = this.etcd.judicator/leader.set_if_equal(prev_val==this.name, this.name, ttl=ttl)
        IF success == true:
            WHILE true:
                success = this.mongodb.tasks.find_and_set(done==false,executor!=NULL, current_time>expire_time, executor=NULL, status=retrying)
                if success == false:
                    BREAK
            WHILE true:
                success = this.mongodb.executors.find_and_delete(current_time>expire_time + duration)
                if success == false:
                    BREAK

Register():
    WHILE true:
        sleep(duration)
        this.etcd.judicator/service/this.name.set(this.address, ttl=ttl)

Add(t):
    this.mongodb.tasks.add(t, executor=NULL, status=pending)

Cancel(t):
    this.mongodb.tasks.find_and_set(id==t, done==false, executor=NULL, status=cancelled, done=true)

Search(conds):
    RETURN this.mongodb.tasks.find(conds==conds)

Get(t):
    RETURN this.mongodb.tasks.find(id==t)

Report(e, complete, executing, vacant):
    result = this.mongodb.executors.find_and_set(this.name==e, report_time=current_time)
    IF result == NULL:
        this.mongodb.executors.insert(e)
    FOR t in complete:
        this.mongodb.tasks.find_and_set(id==t.id, executor==e, executor=NULL, report_time=current_time)
        delete_list.append(t)
    FOR t IN executing:
        result = this.mongodb.tasks.find_and_set(id==t.id, executor==e, report_time=current_time)
        IF result == NULL:
            delete_list.append(t)
    WHILE true:
        result = this.mongodb.tasks.find_and_set(id NOT IN executing, executor==e, done=false, executor=NULL, status=retrying)
        IF NOT result:
            BREAK
        delete_list.append(result)
    WHILE vacant:
        t = this.mongodb.tasks.find_and_set(executor==NULL, done==false, executor=e, report_time=current_time)
        IF t == NULL:
            BREAK
        add_list.append(t)
        vacant = vacant - 1
    RETURN delete_list, add_list
```

#### Boot
```
read_argments()
modify_config_files()
services = {etcd: NULL, mongodb: NULL, main: NULL}
FOR service IN services:
    file = open(service.pid_file, "w")
    file.write(-1)
    file.close()
WHILE true:
    FOR service IN services:
        file = open(service.pid_file, "r+")
        IF file.get_lock(asycn=true):
            IF services[service] == NULL OR services[service].poll() != NULL:
                services[service] = run services[service]
                file.truncate()
                file.write(services[service].pid)
            file.release_lock()
        file.close()
    sleep(duration)
```