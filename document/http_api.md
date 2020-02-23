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

- **URL:** /api/test
- **Method:** POST
- **Format:** Form
- **URL parameters:** None
- **Form structure:**

| key | type | meaning | required | default | note | example |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| user | int | id of user | true | | must between 0 and 2147483647 | 0 |
| compile_source | file | execution | true | | a zip file, this will override compile_source_name and compile_source_str when it is not empty | |
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


### Search


### Get


### Executors


### Judicators


