namespace py judicator_rpc

struct Compile {
    1: binary source,
    2: binary command,
    3: i32 timeout
}

struct Execute {
    1: binary input,
    2: binary data,
    3: binary command,
    4: i32 timeout,
    5: binary standard
}

struct Result {
    1: binary compile_output,
    2: binary compile_error,
    3: binary execute_output,
    4: binary execute_error
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

enum ReturnCode {
    OK = 0,
    ERROR = -1,
    NOT_EXIST = 1
}

struct AddReturn {
    1: ReturnCode result,
    2: string id
}

struct SearchReturn {
    1: ReturnCode result,
    2: list<TaskBrief> tasks
}

struct GetReturn {
    1: ReturnCode result,
    2: Task task
}

struct ReportReturn {
    1: ReturnCode result,
    2: list<TaskBrief> cancel,
    3: list<Task> assign
}

service Judicator {
    ReturnCode ping();
    AddReturn add(Task task);
    ReturnCode cancel(string id);
    SearchReturn search(string id, i32 user, string start_time, string end_time, bool old_to_new, i32 limit);
    GetReturn get(string id);
    ReportReturn report(string executor, list<Task> complete, list<TaskBrief> executing, i32 vacant);
}