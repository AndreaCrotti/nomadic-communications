#!/usr/bin/env sudo python

# ===================
# = analysing tests =
# ===================

import getopt
import re
from errors import *
from utils import *
from vars import *

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
    

# A few important things to analyze to get can be
# Length of the packet
# Arrival time
# Payload

def gnuplot_conf():
    return config_to_dict(GNUPLOT_CONF)

class Plotter(object):
    """Class for plotting during testing"""
    def __init__(self, title, value, maxGraphs = 2):
        if not GNUPLOT:
            LibError("gnuplot", True)
        self.title = title
        self.value = value
        self.items = []
        self.last = []
        self.plotter = Gnuplot.Gnuplot(persist = 1)
        self.plotter.set_string("title", title)
        self.plotter.set_range('yrange', (0,"*"))
        self.plotter.set_label('xlabel', "step")
        self.plotter.set_label('ylabel', self.value)

    def load_conf(self, conf_file):
        """Loading a gnuplot configuration file"""
        self.plotter.load(conf_file)

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

def mean(data):
    return stats.mean(data)

def stdev(data):
    return stats.stdev(data)


class StatData(object):
    """Statistical computations on data"""
    def __init__(self, data):
        self.data = data
        self.mean = stats.mean(data)
        self.stdev = stats.stdev(data)
    
    def __str__(self):
        return "\n".join(["values:\t" + str(self.data), "mean:\t" + str(self.mean), "stdev:\t" + str(self.stdev)])