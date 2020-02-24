# HTTP API

This page describes HTTP interface provided by Gateway in details. In fact, the website held by the Gateay
also uses these APIs.

### Common Code

##### Response Code

| value | meaning |
| :---: | :---: |
| 0 | ok |
| 1 | error |
| 2 | not exist |
| 3 | too large |
| 4 | invalid input |

##### Task Status Code

| value | meaning |
| :---: | :---: |
| 0 | pending |
| 1 | compiling |
| 2 | compile failed |
| 3 | running |
| 4 | run failed |
| 5 | success |
| 6 | retrying |
| 7 | cancelled |
| 8 | unknown error |

### Test

Test if the web server is working.

- **URL:** /api/test
- **Method:** GET
- **URL parameters:** None
- **Response formate:** Text
- **Response:** "Khala gateway server is working."

### Add

Add a task to the system.

- **URL:** /api/task
- **Method:** POST
- **Format:** Form
- **URL parameters:** None
- **Form structure:**

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| user | int | id of user | true | | must between 0 and 2147483647 | 0 |
| compile_source | file | compilation source | true | | a zip file, this will override compile_source_name and compile_source_str when it is not empty | |
| compile_source_name | string | compilation source file name | true | | | main.cpp |
| compile_source_str | string | compilation source file content | true | | | int main() {} |
| compile_command | string | compilation command | true | | | g++ -o main main.cpp |
| compile_timeout | int | compilation time out | true | | must between 0 and 2147483647 | 1 |
| execute_input | string | input stream of compiled program | true | | | 1 2 |
| execute_data | file | extra execution data | true | | a zip file, this will override execute_data_name and execute_data_str when it is not empty | |
| execute_data_name | string | extra execution data file name | true | | | raw.dat |
| execute_data_str | string | extra execution data file content | true | | | data string |
| execute_command | string | execution command | true | | | ./main |
| execute_timeout | int | execution time out | true | | must between 0 and 2147483647 | 1 |
| execute_standard | string | execution standard output | true | | this will not be used during task execution | 3 |

- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | response code | true | false | see common response code | 0 |
| id | string | id of newly added task | true | true | a string with length of 24 | 0123456789abcdef01234567 |

### Cancel

Cancel an undone task.

- **URL:** /api/task
- **Method:** DELETE
- **URL parameters:** 

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | exact task id | true | | a string with length of 24 | 0123456789abcdef01234567 |

- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | response code | true | false | see common response code | 0 |

### Search

Search tasks according to conditions

- **URL:** /api/task/list
- **Method:** GET
- **URL parameters:** 

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | exact task id | false | null | a string with length of 24 | 0123456789abcdef01234567 |
| user | int | id of user owning the task | false | null | must between 0 and 2147483647 | 0 |
| start_time | string | earliest add time of the task | false | null | should be in a valid time format | 2020-01-01T00:00:00Z |
| end_time | string | latest add time of the task | false | null | should be in a valid time format | 2020-01-01T23:59:59Z |
| old_to_new | string | if the result should be ranker from old to new | false | null | any non-empty string | 1 |
| limit | int | max size of the search result | false | 0 | must between 0 and 2147483647, if it is 0 meanings no limitation | 10 |
| page | int | the page number of result | false | 0 | must between 0 and 2147483647, start from 0 | 0 |

- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | response code | true | false | see common response code | 0 |
| pages | int | total pages of all result | true | false | must between 0 and 2147483647 | 1 |
| tasks | list<BriefTask> | search result | true | false | see below for BriefTask structure | |

- **BriefTask structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | exact task id | true | false | a string with length of 24 | 0123456789abcdef01234567 |
| user | int | id of user | true | false | must between 0 and 2147483647 | 0 |
| add_time | string | time when the task is added | true | false | either empty or in iso format | 2020-01-01T00:00:00Z |
| done | bool | if the task has been done | true | false | | true |
| status | int | status code of the task | true | false | see common task status code | 1 |
| executor | string | name of Executor executing the task | true | true | | executor.1 |
| report_time | string | time of last report from executor | true | false | either empty or in iso format | 2020-01-01T23:59:59Z |

### Get

Get a task in details.

- **URL:** /api/task
- **Method:** GET
- **URL parameters:** 

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | exact task id | false | null | a string with length of 24 | 0123456789abcdef01234567 |
| file | string | if requesting any particular result file | false | null | see below | execute_output |
| no_truncate | string | string | if the long text in result should not be truncate | false | false | only work when not getting a file | 1 |

- **Zip files can be requested:** compile_source, execute_data
- **Text files can be requested:** compile_command, execute_input, execute_command, execute_standard, compile_output, 
compile_error, execute_output, execute_error.

- **Response format:** binary when requesting a file, or JSON
- **Response structure when returning JSON:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | response code | true | false | see common response code | 0 |
| tasks | Task | search result | true | true | see below for Task structure | |

- **Task structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | exact task id | true | false | a string with length of 24 | 0123456789abcdef01234567 |
| user | int | id of user | true | false | must between 0 and 2147483647 | 0 |
| add_time | string | time when the task is added | true | false | either empty or in iso format | 2020-01-01T00:00:00Z |
| done | bool | if the task has been done | true | false | | true |
| status | int | status code of the task | true | false | see common task status code | 1 |
| executor | string | name of Executor executing the task | true | true | | executor.1 |
| report_time | string | time of last report from executor | true | false | either empty or in iso format | 2020-01-01T23:59:59Z |
| compile | Compile | compilation parameters description | true | true | see below for Compile structure | |
| execute | Execute | execution parameters description | true | true | see below for Execute structure | |
| result | Result | result of the task | true | true | see below for Result structure | |

- **Compile structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| source | boot | if there is a compilation source zip file for the task | true | false | | true |
| command | string | compilation command | true | false | | g++ -o main main.cpp |
| timeout | int | compilation time out | true | false | must between 0 and 2147483647 | 1 |

- **Execute structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| input | string | input stream of compiled program | true | false | | 1 2 |
| data | boot | if there is a extra execution data zip file for the task | true | false | | true |
| execute_command | string | execution command | true | false | | ./main |
| execute_timeout | int | execution time out | true | false | must between 0 and 2147483647 | 1 |
| execute_standard | string | execution standard output | true | false | | 3 |

### Executors


### Judicators


