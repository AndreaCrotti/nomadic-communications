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

GNUPLOT = False
try:
    import Gnuplot
except ImportError:
    print "unable to plot"
    GNUPLOT = True

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


def get_max_speed(mode, speed):
    """Getting the theoretical max speed achievable"""
    return Speed(speed, 'Mb').translate('KB')

class DataSet(object):
    """General class for handling sets of data"""
    def __init__(self, data, title, xaxis, yaxis, gnuplot_conf, format="default"):
        """The other possible formats are defined in gnuplot configuration file.
        The yaxis must be passed also
        """
        self.data = data
        self.title = title
        self.format = format
        self.xaxis = xaxis
        self.yaxis = yaxis
        self.gnuplot_conf = gnuplot_conf
    
    def to_gnuplot(self):
        """Creates a GnuplotData object
        setting the style accordingly with che configuratin"""
        gp = Gnuplot.Data(self.data)
        if self.gnuplot_conf.has_key(self.format):
            gp.set_style(style)
        return gp

class Plotter(object):
    """Class for plotting during testing"""
    def __init__(self, title, value, maxGraphs = 2):
        if not GNUPLOT:
            LibError("gnuplot", True)
        self.title = title
        self.value = value
        self.items = []
        self.plotter = Gnuplot.Gnuplot(persist = 1)
        self.set_defaults()
    
    def set_defaults(self):
        """Setting some defaults confs"""
        self.plotter.set_string("title", self.title)
        self.plotter.set_range('yrange', (0,"*"))
        self.plotter.set_label('xlabel', "step")
        self.plotter.set_label('ylabel', self.value)
    
    def set_style(self, style):
        # TODO set correct options
        pass
        # self.plotter.

    def load_conf(self, conf_file):
        """Loading a gnuplot configuration file"""
        self.plotter.load(conf_file)

    def add_data(self, data):
        """Add another dataset, which must be 
        GnuplotData instance with all the parameters
        already set"""
        self.items.append(data)

    def plot(self):
        """docstring for plot"""
        self.plotter.plot(*self.items)
    
    def save(self, filename):
        print "saving graph to %s" % filename
        self.plotter.hardcopy(filename=filename, eps=True, color=True)


class StatData(object):
    """Statistical computations on data"""
    def __init__(self, data):
        self.data = data
        self.mean = stats.mean(data)
        self.stdev = stats.stdev(data)
    
    def __str__(self):
        return "\n".join(["values:\t" + str(self.data), "mean:\t" + str(self.mean), "stdev:\t" + str(self.stdev)])