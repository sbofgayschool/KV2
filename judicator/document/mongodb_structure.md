#### Task specifies
```
{
    "_id": ObjectId -> Auto generated id,
    "user": Int -> User id,
    "compile": -> Compile information
    {
        "source": Binary -> Zipped source,
        "command": String -> Compile command,
        "timeout": Int -> Compile timeout
    },
    "execute": -> Execute information
    {
        "data": Binary -> Zipped input data,
        "command": String -> Execute command,
        "timeout": Int -> Execute timeout,
        "standard": Binary -> Zipped standard output
    },
    "done": Boolean -> If the task has been done,
    "status": Int -> Current status,
    "executor": String -> Executor hostname,
    "report_time": Date -> Last report time,
    "result":
    {
        "compile": Binary -> Zipped compile output,
        "execute": Binary -> Zipped execute output
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