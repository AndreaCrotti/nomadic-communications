#!/usr/bin/env python

# Generating options for iperf

CONN = {"tcp" : "-t", "udp" : "-u"}
BAND = [1, 10]
DUAL = {"dual" : "-d", "single" : ""}

for c in CONN.keys():
    for b in BAND:
        for d in DUAL.keys():
            print CONN[c], b, DUAL[d]