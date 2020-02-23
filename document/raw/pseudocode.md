#### Boot
```
run():
    load_args(boot)
    FOR s IN services:
        load_args(s)
    parse_args()
    config = load_config(boot)
    FOR s IN services:
        write_config(s)
    LOOP UNTIL SIGINT:
        FOR s IN services:
            s.pid_file.lock()
            IF NOT s.process.running:
                s.process = subprocess.run(s)
                s.pid_file.write(s.process.pid)
            s.pid_file.unlock()
        sleep(config.interval)
    FOR s IN services:
        s.process.kill()
        s.process.join()
    RETURN
```

#### Etcd
```
check():
    sleep(config.interval)
    IF NOT etcd_process.working:
        etcd_process.kill()
    RETURN

run():
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
                remote_etcd = EtcdProxy(config.cluster.client)
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

register():
    sleep(config.interval)
    IF NOT mongodb_process.working:
        mongodb_process.kill()
        RETURN
    IF local_etcd.insert(init_key, config.address):
        local_mongodb.init_replica_set()
    local_etcd.set(reg_key, config.address)
    WHILE working:
        sleep(config.interval)
        IF local_mongodb.is_primary():
            registered_member = local_etcd.get_list(reg_key)
            replica_set_member = local_mongodb.get_member()
            local_mongodb.remove_member(replica_set_membger - registered_member)
            local_mongodb.add_member(registered_member - replica_set_member)
    RETURN

run():
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
run():
    config = load_config(uwsgi)
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
global working = TRUE

register():
    WHILE working:
        sleep(config.interval)
        local_etcd.set(reg_key, config.address)
    local_etcd.delete(reg_key, config.address)
    RETURN

lead():
    WHILE working:
        sleep(config.interval)
        local_etcd.insert(lead_key, config.address)
        IF local_etcd.set(lead_key, config.address, prev_value=config.address, ttl=config.ttl):
            expire_time = current_time() - config.longest_duration
            mongodb.task.find(done=FALSE, executor!=NULL, report_time<expire_time)
                .set(executor=NULL, status=retrying)
            mongodb.executor.find(report_time<expire_time).delete()
    RETURN

Service.ping():
    RETURN TRUE

Service.add(task):
    id = mongodb.task.add(task)
    RETURN id

Service.cancel(id):
    res = mongodb.task.find(id=id, done=FALSE).set(executor=NULL, done=True, status=cancelled)
    RETURN res

Service.search(condition):
    res = mongodb.task.find(condition).simplifiy()
    cnt = res.count()
    RETURN res, cnt

Service.get(id)
    RETURN mongodb.task.find(id=id)

Service.report(executor, complete_task, executing_task, vacant):
    mongodb.executor.find(executor=executor).set(report_time=current_time())
    cancel_task = []
    FOR task IN complete_task:
        mongodb.task.find(id=task.id, executor=executor)
            .set(done=TRUE, executor=NULL, status=stask.status, report_time=current_time(), result=task.result)
        cancel_task.append(task.id)
    FOR task IN executing_task:
        IF NOT mongodb.task.find(id=task.id, executor=executor).set(status=task.status, report_time=current_time()):
            cancel_task.append(task.id)
    FOR task IN (mongodb.task.find(executor=executor) - executing_list):
        mongodb.task.find(id=task.id).set(executor=NULL, status=retrying)
    assign_task = mongodb.task.find(executor=NULL, done=FALSE).limit(vacant)
    assign_task.set(report_time=current_time(), executor=executor)
    RETURN cancel_task, assign_task

Service.executors():
    RETURN mongodb.executor.find()

run():
    config = load_config(judicator)
    register_thread = thread.run(register)
    lead_thread = thread.run(lead)
    server = Service
    server.serve(until=SIGINT)
    working = FALSE
    register_thread.join()
    RETURN
```

#### Executor Main
```
global tasks = {}, lock = Lock()

def execute(task):
    generate_files(task)
    lock.lock()
    cancel = task.cancel
    IF NOT cancel:
        task.status = compiling
        task.process = subprocess.run(task.compile_config)
    ELSE:
        task.done = TRUE
    lock.unlock()
    IF cancel:
        clean_up(task)
        RETURN
    res = task.process.join()
    IF res == TIMEOUT:
        task.process.kill()
    lock.lock()
    collect_compile_result(task)
    IF res != 0:
        task.status = compile_failed
        task.done = TRUE
        task.process = NULL
    ELSE:
        task.status = running
        task.process = subprocess.run(task.run_config)
    lock.unlock()
    IF res != 0:
        clean_up(task)
        RETURN
    res = task.process.join()
    IF res == TIMEOUT:
        task.process.kill()
    lock.lock()
    collect_execute_result(task)
    IF res != 0:
        task.status = run_failed
    ELSE:
        task.status = success
    task.done = TRUE
    task.process = NULL
    lock.unlock()
    clean_up(task)
    RETURN

report(complete, executing, vacant):
    RETURN choose_one(local_etcd.get(judicator_key)).report(config.name, complete, executing, vacant)

run():
    config = load_config(executor)
    LOOP UNTIL SIGINT:
        complete = [], executing = [], vacant = config.vacant
        lock.lock():
            FOR task IN tasks:
                IF NOT task.cancel:
                    IF task.thread.running:
                        executing.append(task)
                        vacant = vacant - 1
                    ELSE:
                        complete.append(task)
        lock.unlock()
        cancel, assign = report(complete, executing, vacant)
        lock.lock()
        FOR task IN cancel:
            task.cancel = TRUE
            IF task.process:
                task.process.kill()
        FOR task IN tasks:
            IF task.cancel AND NOT task.thread.running:
                tasks.remove(cancel)
        FOR task IN assign:
            tasks.add(task)
            task.process = NULL
            task.cancel = FALSE
            task.thread = thread.run(execute, task)
        lock.unlock()
        sleep(config.interval)
    lock.lock()
    FOR task in tasks:
        IF task.process:
            task.process.kill()
    RETURN
```

#### Gateway Server
```
Server.test():
    RETURN OK

Server.add(task):
    RETURN choose_one(local_etcd.get(judicator_key)).add(task)

Server.cancel(id):
    RETURN choose_one(local_etcd.get(judicator_key)).cancel(id)

Server.search(condition):
    RETURN choose_one(local_etcd.get(judicator_key)).search(condition)

Server.get(id):
    RETURN choose_one(local_etcd.get(judicator_key)).get(id)

Server.executors():
    RETURN choose_one(local_etcd.get(judicator_key)).executors()

Server.judicators():
    RETURN local_etcd.get(judicator_key)

Server.resource(path):
    RETURN static_file("res/" + path)

Server.webpage(path):
    RETURN render_template(path)
```
