#### Task specifies
```
{
    "_id": ObjectId -> Auto generated id,
    "user": Int -> User id,
    "compile":
    {
        "source": Binary,
        "command": Binary，
        "timeout": Int
    },
    "execute":
    {
        "data": Binary,
        "command": Binary,
        "timeout": Int,
        "standard": Binary
    },
    "done": Boolean,
    "status": Int,
    "executor": String,
    "report_time": String,
    "result":
    {
        "compile": Binary,
        "execute": Binary
    }
}
```

#### Executor
```
{
    "_id": ObjectId -> Auto generated id,
    "hostname": String -> Hostname of the executor,
    "report_time": String -> Last report time
}
```