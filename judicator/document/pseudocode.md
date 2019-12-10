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
        IF this.mongodb IN remote.mongodb.member_list:
            BREAK
        ELSE:
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
        success = this.etcd.judicator/leader.set_if_empty(this.address, ttl=ttl)
        IF success == false:
            success = this.etcd.judicator/leader.set_if_equal(this.address, this.address, ttl=ttl)
        IF success == true:
            WHILE true:
                success = this.mongodb.tasks.find_and_set(done==false, current_time>expire_time, executor=NULL, status=retrying)
                if success == false:
                    BREAK
            WHILE true:
                success = this.mongodb.executors.find_and_delete(current_time>expire_time + duration)
                if success == false:
                    BREAK

Register():
    key = "rpc_" + self.address
    WHILE true:
        sleep(duration)
        this.etcd.judicator/key.set(self.address, ttl=ttl)

Add(t):
    this.mongodb.tasks.add(t, executor=NULL, status=pending)

Cancel(t):
    this.mongodb.tasks.find_and_set(id==t, done==false, executor=NULL, status=cancelled, done=true)

Search(conds):
    RETURN this.mongodb.tasks.find(conds==conds)

Get(t):
    RETURN this.mongodb.tasks.find(id==t)

Report(e, tasks, vacant):
    this.mongodb.executors.find_and_set(address==e, report_time=current_time)
    FOR t IN tasks:
        IF t.done == true:
            executor = NULL
        ELSE
            executor = e
        result = this.mongodb.tasks.find_and_set(id==t, executor=executor, report_time=current_time)
        IF result == NULL OR result.executor != e:
            delete_list.append(result)
    WHILE vacant:
        t = this.mongodb.tasks.find_and_set(executor==NULL, done==false, executor=e)
        IF t == NULL:
            BREAK
        add_list.append(t)
        vacant = vacant - 1
    RETURN delete_list, add_list
```