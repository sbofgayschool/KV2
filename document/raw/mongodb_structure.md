#### Task specifies
```
{
    "_id": ObjectId -> Auto generated id,
    "user": Int -> User id,
    "compile": -> Compile information
    {
        "source": Binary -> Zip file containing source,
        "command": Binary -> Zipped compile command,
        "timeout": Int -> Compile timeout
    },
    "execute": -> Execute information
    {
        "input": Binary -> Zipped input data used as stdin,
        "data: Binary -> Zip file containing extra data,
        "command": Binary -> Zipped execute command,
        "timeout": Int -> Execute timeout,
        "standard": Binary -> Zipped standard output
    },
    "add_time": Date -> Time when this task being added,
    "done": Boolean -> If the task has been done,
    "status": Int -> Current status,
    "executor": String -> Executor hostname,
    "report_time": Date -> Last report time,
    "result":
    {
        "compile_output": Binary -> Zipped compile stdout output,
        "compile_error": Binary -> Zipped compile stderr output,
        "execute_output": Binary -> Zipped execute stdout output,
        "execute_error": Binary -> Zipped execute stderr output,
    }
}
```

#### Executor
```
{
    "_id": ObjectId -> Auto generated id,
    "hostname": String -> Hostname of the executor,
    "report_time": Date -> Last report time
}
```