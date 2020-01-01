#!/usr/bin/env bash

rm -rf ./data
mkdir ./data
mkdir ./data/etcd
mkdir ./data/server

rm -f config/*.*

rm -rf ./log
mkdir ./log
mkdir ./log/boot
mkdir ./log/etcd
mkdir ./log/server
mkdir ./log/uwsgi
