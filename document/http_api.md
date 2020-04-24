# HTTP API

This page describes HTTP interface provided by Gateway in details. In fact, the website held by the Gateay
also uses these APIs.

*RPC API is very similar to this. Find a Judicator on etcd first if you wish to invoke RPC request directly.*

*For RPC IDL, please see [rpc/judicator.thrift](../rpc/judicator.thrift).*

## Common Code

#### Response Code

| value | meaning |
| :---: | :---: |
| 0 | OK |
| 1 | Error |
| 2 | Not exist |
| 3 | Too large |
| 4 | Invalid input |

#### Task Status Code

| value | meaning |
| :---: | :---: |
| 0 | Pending |
| 1 | Compiling |
| 2 | Compile failed |
| 3 | Running |
| 4 | Run failed |
| 5 | Success |
| 6 | Retrying |
| 7 | Cancelled |
| 8 | Unknown error |

## Test

Test if the web server is working.

- **URL:** /api/test
- **Method:** GET
- **URL parameters:** None
- **Response formate:** Text
- **Response:** "Khala gateway server is working."

## Add

Add a task to the system.

- **URL:** /api/task
- **Method:** POST
- **Format:** Form
- **URL parameters:** None
- **Form structure:**

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| user | int | Id of user | true | | must between 0 and 2147483647 | 0 |
| compile_source | file | Compilation source | true | | a zip file, this will override compile_source_name and compile_source_str when it is not empty | |
| compile_source_name | string | Compilation source file name | true | | | main.cpp |
| compile_source_str | string | Compilation source file content | true | | | int main() {} |
| compile_command | string | Compilation command | true | | | g++ -o main main.cpp |
| compile_timeout | int | Compilation time out | true | | 0 for unlimited, must between 0 and 2147483647 | 1 |
| execute_input | string | Input stream of compiled program | true | | | 1 2 |
| execute_data | file | Extra execution data | true | | a zip file, this will override execute_data_name and execute_data_str when it is not empty | |
| execute_data_name | string | Extra execution data file name | true | | | raw.dat |
| execute_data_str | string | Extra execution data file content | true | | | data string |
| execute_command | string | Execution command | true | | | ./main |
| execute_timeout | int | Execution time out | true | | 0 for unlimited, must between 0 and 2147483647 | 1 |
| execute_standard | string | Execution standard output | true | | this will not be used during task execution | 3 |

- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | Response code | true | false | see common response code | 0 |
| id | string | Id of newly added task | true | true | a string with length of 24 | 0123456789abcdef01234567 |

## Cancel

Cancel an undone task.

- **URL:** /api/task
- **Method:** DELETE
- **URL parameters:** 

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | Exact task id | true | | a string with length of 24 | 0123456789abcdef01234567 |

- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | Response code | true | false | see common response code | 0 |

## Search

Search tasks according to conditions

- **URL:** /api/task/list
- **Method:** GET
- **URL parameters:** 

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | Exact task id | false | null | a string with length of 24 | 0123456789abcdef01234567 |
| user | int | Id of user owning the task | false | null | must between 0 and 2147483647 | 0 |
| start_time | string | Earliest add time of the task | false | null | should be in a valid time format | 2020-01-01T00:00:00 |
| end_time | string | Latest add time of the task | false | null | should be in a valid time format | 2020-01-01T23:59:59 |
| old_to_new | string | If the result should be ranker from old to new | false | null | any non-empty string | 1 |
| limit | int | Max size of the search result | false | 0 | must between 0 and 2147483647, if it is 0 meanings no limitation | 10 |
| page | int | The page number of result | false | 0 | must between 0 and 2147483647, start from 0 | 0 |

- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | Response code | true | false | see common response code | 0 |
| pages | int | Total pages of all result | true | false | must between 0 and 2147483647 | 1 |
| tasks | list<BriefTask> | Search result | true | false | see below for BriefTask structure | |

- **BriefTask structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | Exact task id | true | false | a string with length of 24 | 0123456789abcdef01234567 |
| user | int | Id of user | true | false | must between 0 and 2147483647 | 0 |
| add_time | string | Time when the task is added | true | false | either empty or in iso format | 2020-01-01T00:00:00.000000 |
| done | bool | If the task has been done | true | false | | true |
| status | int | Status code of the task | true | false | see common task status code | 1 |
| executor | string | Name of Executor executing the task | true | true | | executor.1 |
| report_time | string | Time of last report from executor | true | false | either empty or in iso format | 2020-01-01T23:59:59.000000 |

## Get

Get a task in details.

- **URL:** /api/task
- **Method:** GET
- **URL parameters:** 

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | Exact task id | false | null | a string with length of 24 | 0123456789abcdef01234567 |
| file | string | If requesting any particular result file | false | null | see below for possible values | execute_output |
| no_truncate | string | if the long text in result should not be truncate | false | null | only work when not getting a file | 1 |

- **Zip files can be requested:** compile_source, execute_data
- **Text files can be requested:** compile_command, execute_input, execute_command, execute_standard, compile_output, 
compile_error, execute_output, execute_error.

- **Response format:** binary when requesting a file, or JSON
- **Response structure when returning JSON:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | Response code | true | false | see common response code | 0 |
| task | Task | Search result | true | true | see below for Task structure | |

- **Task structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | Exact task id | true | false | a string with length of 24 | 0123456789abcdef01234567 |
| user | int | Id of user | true | false | must between 0 and 2147483647 | 0 |
| add_time | string | Time when the task is added | true | false | either empty or in iso format | 2020-01-01T00:00:00.000000 |
| done | bool | If the task has been done | true | false | | true |
| status | int | Status code of the task | true | false | see common task status code | 1 |
| executor | string | Name of Executor executing the task | true | true | | executor.1 |
| report_time | string | Time of last report from executor | true | false | either empty or in iso format | 2020-01-01T23:59:59.000000 |
| compile | Compile | Compilation parameters description | true | true | see below for Compile structure | |
| execute | Execute | Execution parameters description | true | true | see below for Execute structure | |
| result | Result | Result of the task | true | true | see below for Result structure | |

- **Compile structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| source | bool | If there is a compilation source zip file for the task | true | false | | true |
| command | string | Compilation command | true | false | | g++ -o main main.cpp |
| timeout | int | Compilation time out | true | false | 0 for unlimited, must between 0 and 2147483647 | 1 |

- **Execute structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| input | string | Input stream of compiled program | true | false | | 1 2 |
| data | bool | If there is a extra execution data zip file for the task | true | false | | true |
| execute_command | string | Execution command | true | false | | ./main |
| execute_timeout | int | Execution time out | true | false | 0 for unlimited, must between 0 and 2147483647 | 1 |
| execute_standard | string | Execution standard output | true | false | | 3 |

- **Result structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| compile_output | string | Output stream of compilation | true | false | | all done |
| compile_error | string | Error stream of compilation | true | false | | some error |
| execute_output | string | Output stream of execution | true | false | | 3 |
| execute_error | string | Error stream of execution | true | false | | some error |

## Executors

Get the list of working Executors.

- **URL:** /api/executors
- **Method:** GET
- **URL parameters:** None
- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | Response code | true | false | see common response code | 0 |
| executors | list<Executor> | Working Executors | true | false | see below for Executor structure | |

- **Executor structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| id | string | MongoDB id of Executor | true | false | a string with length of 24 | 0123456789abcdef01234567 |
| hostname | string | Hostname of Executor | true | false | | executor.1 |
| report_time | time | Time of the last report from the executor | true | false | in iso format | 2020-01-01T12:00:00.000000 |

## Judicators

Get the list of working Judicators.

- **URL:** /api/judicators
- **Method:** GET
- **URL parameters:** None
- **Response format:** JSON
- **Response structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| result | int | Response code | true | false | see common response code | 0 |
| judicators | list<Judicator> | Working Judicators | true | false | see below for Judicator structure | |

- **Judicator structure:**

| key | type | meaning | must exist | can be null | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| name | string | Registered path of Judicator | true | false | | /judicators/judicator.1 |
| address | string | Address of Judicator | true | false | | localhost:4000 |
