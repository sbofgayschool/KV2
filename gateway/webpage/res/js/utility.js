var test = true;

var result_code = {
    0: "Success!",
    1: "Error!",
    2: "Not Exist!"
};

var task_status = {
    0: "pending",
    1: "compiling",
    2: "compile failed",
    3: "running",
    4: "run failed",
    5: "success",
    6: "retrying",
    7: "cancelled",
    8: "error"
};

var page_limit = 10;

function handle_error(error)
{
    if (typeof(error) === "number")
        show_message(true, "alert-danger", "Error!", result_code[error]);
    else
        show_message(true, "alert-danger", "Error!", "Server returned error code: " + error.status + "!");
}

function cancel_task(id, success, clean_message)
{
    if (clean_message)
        show_message(false);
    ajax(
        "api/task",
        {"id": id},
        null,
        "DELETE",
        success
    )
}

function ajax(url, param, data, method, success, json)
{
    if (param)
        url += "?" + $.param(param);
    var args = {
        url: url,
        type: method,
        data: data,
        success: function (data)
        {
            if (!data["result"])
                success(data);
            else
                handle_error(data["result"]);
        },
        error: function (error) {handle_error(error);}
    };
    if (data === null)
        delete args["data"];
    else if (json === true)
    {
        args["contentType"] = "application/json;charset=utf-8;";
        args["dataType"] = "json";
        args["data"] = JSON.stringify(data);
    }
    else if (json === false)
    {
        args["contentType"] = false;
        args["processData"] = false;
    }
    $.ajax(args);
}