#!/usr/bin/env bash
PY=$(python --version 2>&1)
GP=$(gnuplot --version)
SYS=$(uname -v)

echo "python: $PY"
echo "gnuplot: $GP"
echo "sys: $SYS"