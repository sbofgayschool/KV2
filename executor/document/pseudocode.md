#### Ectd daemon
```
IF etcd.dir exists:
    run this.etcd --proxy
ELSE:
    IF initializing:
        run this.etcd --initialize --proxy
    ELSE:
        run this.etcd --join --proxy
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

#### Main
```
WHILE true:
    sleep(duration)
    lock()
    FOR t in tasks:
        IF t.cancel == false:
            content.append(t)
        IF t.done == true:
            vacant = vacant + 1
    unlock()
    rpc = this.etcd.get_rpc()
    cancel_list, add_list = rpc.report(this.address, content, vacant)
    lock()
        FOR t in cancel_list:
            t.cancel = true
            IF tasks.t.proc:
                tasks.t.proc.kill()
        FOR t in tasks:
            IF t.done == true:
                t.thread.join()
                IF t.cancel == true:
                    tasks.remove(t)
                    clean_file(t)
        FOR t in add_list:
            create_file(t)
            tasks.append(t)
            t.thread = Thread(Execute, t)
            t.thread.run()
    unlock()

Execute(t):
    lock()
    IF t.cancel:
        END
    t.status = compiling
    t.proc = run compiler 1>output 2>error
    unlock()
    TRY:
        success = t.proc.wait(timeout)
    EXCEPT:
        success = false
        t.proc.kill()
        t.proc.wait()
    lock()
    IF success == false:
        t.status = compile_failed
        t.done = true
        t.proc = NULL
        unlock()
        END
    t.status = running
    t.proc = run program 0<input 1>output 2>error
    unlock()
    TRY:
        success = t.proc.wait(timeout)
    EXCEPT:
        success = false
        t.proc.kill()
        t.proc.wait()
    lock()
    IF success == false:
        t.status = run_failed
    ELSE:
        t.status = success
    t.done = true
    t.proc = NULL
    unlock()
```