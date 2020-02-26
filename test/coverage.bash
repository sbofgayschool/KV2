#!/usr/bin/env bash

bash clean.bash
if [[ $# == 0 ]]; then
    i=0
    for file in `ls`; do
        if [[ $file =~ ^(test_).+(\.py)$ ]]; then
            files[$i]=$file;
            ((i++));
        fi
    done
else
    files=${@:1};
fi
for file in ${files[*]};
do
    echo "Testing $file ..."
    echo ""
    coverage-3.7 run --rcfile=.coveragerc --concurrency=multiprocessing --parallel-mode $file
    echo ""
    sleep 5
done
coverage-3.7 combine
coverage-3.7 report
coverage-3.7 html
