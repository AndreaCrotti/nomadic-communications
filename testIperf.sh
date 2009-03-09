#!/usr/bin/env bash
# possible parameters are
# we set the options and run NTEST for every possible
HOST=192.168.10.30
CMD="sudo iperf -u -c $HOST"
RESULT="result.txt"
NTEST=20

for (( i = 0; i < 20; i++ )); do
  $CMD >> $RESULT
done