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
    5: string add_time,
    6: bool done,
    7: i32 status,
    8: string executor,
    9: string report_time,
    10: Result result
}

struct TaskBrief {
    1: string id,
    2: i32 user,
    3: string add_time,
    4: bool done,
    5: i32 status,
    6: string executor,
    7: string report_time
}

struct Executor {
    1: string id,
    2: string hostname,
    3: string report_time
}

enum ReturnCode {
    OK = 0,
    ERROR = 1,
    NOT_EXIST = 2,
    TOO_LARGE = 3,
    INVALID_INPUT = 4
}

struct AddReturn {
    1: ReturnCode result,
    2: string id
}

struct SearchReturn {
    1: ReturnCode result,
    2: i32 pages,
    3: list<TaskBrief> tasks
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

struct ExecutorsReturn {
    1: ReturnCode result,
    2: list<Executor> executors
}

service Judicator {
    ReturnCode ping();
    AddReturn add(1: Task task);
    ReturnCode cancel(1: string id);
    SearchReturn search(1: string id, 2:i32 user, 3: string start_time, 4: string end_time, 5: bool old_to_new, 6: i32 limit, 7: i32 page);
    GetReturn get(1: string id);
    ReportReturn report(1: string executor, 2: list<Task> complete, 3: list<TaskBrief> executing, 4: i32 vacant);

    ExecutorsReturn executors();
}
