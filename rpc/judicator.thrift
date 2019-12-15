namespace py judicator_rpc

struct Compile {
    1: binary source,
    2: binary command,
    3: i32 timeout
}

struct Execute {
    1: binary source,
    2: binary command,
    3: i32 timeout,
    4: binary standard
}

struct Result {
    1: binary compile,
    2: binary execute
}

struct Task {
    1: string id,
    2: i32 user,
    3: Compile compile,
    4: Execute execute,
    5: bool done,
    6: i32 status,
    7: string executor,
    8: string report_time,
    9: Result result
}

struct TaskBrief {
    1: string id,
    2: i32 user,
    3: bool done,
    4: i32 status,
    5: string executor,
    6: string report_time
}

struct Executor {
    1: string id,
    2: string hostname,
    3: string report_time
}

struct NormalReturn {
    1: bool result,
    2: string notice
}

struct TwoLists {
    1: list<TaskBrief> brief,
    2: list<Task> full
}

service Judicator {
    void ping();
    NormalReturn add(Task task);
    NormalReturn cancel(string task_id);
    list<TaskBrief> search(string id, string start_time, string end_time, bool old_to_new, i32 limit);
    Task get(string task_id);
    TwoLists report(string executor, TwoLists tasks, i32 vacant);
}