#### Ectd daemon
```
IF etcd.dir exists:
    run this.etcd
ELSE:
    IF initializing:
        run this.etcd --initialize
    ELSE:
        remote.etcd.add(this.etcd)
        run this.etcd --join
log(this.etcd.output) UNTIL EOF
```

#### MongoDB daemon
```
run this.mongodb
log_and_monitor(this.mongodb.output) UNTIL this.mongodb.started
register_thread = Thread(Register)
register_thread.set_daemon()
register_thread.run()
log(this.mongodb.output) UNTIL EOF

Register:
    etcd.mongodb/primary.set_if_empty(this.mongodb)
    IF etcd.mongodb/primary == this.mongodb:
        this.mongodb.intialize_rs
    ELSE:
        IF this.mongodb IN remote.mongodb.member_list:
            BREAK
        ELSE:
            IF remote.mongodb.vote_member < 7:
                remote.mongodb.add(this.mongodb, vote, priority)
            ELSE:
                remote.mongodb.add(this.mongodb)
    EVERY duration:
        IF this.mongodb.primary_member == this.mongodb:
            etcd.mongodb/primary.set(this.mongodb)
```