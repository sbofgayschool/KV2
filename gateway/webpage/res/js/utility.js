var test = true;

var code_message = {
    0: "Success!",
    1: "Invalid Data!",
    100: "Restaurant not found!",
    101: "Restaurants with the same name and branch exist!",
    150: "Coordinate of the postcode not found!",
    200: "Tag not found!",
    201: "Tags with the same name exist!",
    300: "Cart is empty!",
};

function handle_error(error)
{
    if (typeof(error) === "number")
        show_message(true, "alert-danger", "Error!", code_message[error]);
    else
        show_message(true, "alert-danger", "Error!", "Server returned error code: " + error.status + "!");
}

function go_back(page=1)
{
    window.history.length >= page ? window.history.go(-page) : window.location.href='find_restaurants';
}

function ajax(url, obj, success)
{
    $.ajax({
        url: url,
        type: "POST",
        contentType: "application/json;charset=utf-8;",
        data: JSON.stringify(obj),
        dataType: "json",
        success: function (data)
        {
            if (!data["code"])
                success(data["res"]);
            else
                handle_error(data["code"]);
        },
        error: function (error) {handle_error(error);},
        xhrFields: {withCredentials: test},
        crossDomain: test
    });
}