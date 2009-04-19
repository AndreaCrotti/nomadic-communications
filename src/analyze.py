#!/usr/bin/env sudo python

# ===================
# = analysing tests =
# ===================

import shelve
import getopt
import re

# SCAPY = True
# try:
#     from scapy import *
# except ImportError:
#     print "unable to analyze packets with scapy"
#     SCAPY = False

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

class Plotter:
    """Class for plotting during testing"""
    def __init__(self, title, value, maxGraphs = 2):
        self.title = title
        self.value = value
        self.items = []
        self.last = []
        self.plotter = Gnuplot.Gnuplot(persist = 1)
        self.plotter.set_string("title", title)
        self.plotter.set_range('yrange', (0,"*"))
        self.plotter.set_label('xlabel', "step")
        self.plotter.set_label('ylabel', self.value)

    def add_data(self, data, name):
        """Add another data set"""
        # always keeping last maxGraphs elements in the item list and redraw them
        self.last = data
        new = Gnuplot.Data(data, title = name)
        self.items.append(new)

    def plot(self):
        """docstring for plot"""
        self.plotter.plot(*self.items)
    
    def save(self, filename):
        print "saving graph to %s" % filename
        self.plotter.hardcopy(filename=filename, eps=True, color=True)


class StatData:
    """Statistical computations on data"""
    def __init__(self, data):
        self.data = data
        self.mean = stats.mean(data)
        self.stdev = stats.stdev(data)
    
    def __str__(self):
        return "\n".join(["values:\t" + str(self.data), "mean:\t" + str(self.mean), "stdev:\t" + str(self.stdev)])