#### Ectd daemon
```
IF etcd.dir exists:
    run this.etcd --proxy
ELSE:
    IF initializing:
        run this.etcd --initialize --proxy
    ELSE:
        run this.etcd --join --proxy
log(this.etcd.output) UNTIL EOF
```