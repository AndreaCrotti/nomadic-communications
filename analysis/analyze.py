#!/usr/bin/env sudo python

# ===================
# = analysing tests =
# ===================

import shelve
import getopt
import re
import scapy

SCAPY = True
try:
    from scapy import *
except ImportError:
    print "unable to analyze packets with scapy"
    SCAPY = False

STAT = True
try:
    from statlib import stats
except ImportError, i:
    print "not able to do the statistical analysis"
    STAT = False

GNUPLOT = True
try:
    import Gnuplot
except ImportError, i:
    print "you will be unable to plot in real time"
    GNUPLOT = False
    
DUMP = "traffic/traffic.out"

# A few important things to analyze to get can be
# Length of the packet
# Arrival time
# Payload

def pkg_analyze(pkt):
    while True:
        
        print "Len"


class StatData:
    """Statistical computations on data"""
    def __init__(self, data):
        self.data = data
        self.mean = stats.mean(data)
        self.stdev = stats.stdev(data)
    
    def __str__(self):
        return "\n".join(["values:\t" + str(self.data), "mean:\t" + str(self.mean), "stdev:\t" + str(self.stdev)])