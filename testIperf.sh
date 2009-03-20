#!/usr/bin/env bash
# possible parameters are
# we set the options and run NTEST for every possible

source datas
CMD="iperf -u -c $SERVER"
RESULT="result${date +%d-%M-%H-%m-%s}.txt"
NTEST=10

for (( i = 0; i < NTEST; i++ )); do
  $CMD >> $RESULT
done