// Result code definition
var result_code = {
    0: "Operation succeeded!",
    1: "Error occurs during operation!",
    2: "Specified task not exist!",
    3: "Submitted task too large!",
    4: "Invalid input discovered!"
};

// Task status definition
var task_status = {
    0: "pending",
    1: "compiling",
    2: "compile failed",
    3: "running",
    4: "run failed",
    5: "success",
    6: "retrying",
    7: "cancelled",
    8: "unknown error"
};

// Number of searched tasks on a page
var page_limit = 10;

/**
 * Handle an error by showing message
 * @param error The error
 */
function handle_error(error)
{
    // If it is an error code, show the corresponding string
    // Else, it is an server error, show the code
    if (typeof(error) === "number")
        show_message(true, "alert-danger", "Error!", result_code[error]);
    else
        show_message(true, "alert-danger", "Error!", "Server returned error code: " + error.status + "!");
}

/**
 * Cancel a task
 * @param id Id of the cancelled task
 * @param success Callback function when succeeded
 * @param clean_message If all message should be cleaned before cancellation
 */
function cancel_task(id, success, clean_message)
{
    // Clean the message, if required
    if (clean_message)
        show_message(false);
    // Make the ajax call
    ajax(
        "api/task",
        {"id": id},
        null,
        "DELETE",
        success
    )
}

/**
 * Wrapped ajax call function
 * @param url The url
 * @param param Url parameters
 * @param data Http body
 * @param method Method of the call
 * @param success Callback function when succeeded
 * @param json If the data should be in json format
 */
function ajax(url, param, data, method, success, json)
{
    // Encoded all url params
    if (param)
        url += "?" + $.param(param);
    // Generate args object
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
    // Delete data field, if there is no http body
    // Else if the call should be in json format, encode it
    // Else if the call should be in form format, encode it
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
    // Execute ajax request
    $.ajax(args);
}
