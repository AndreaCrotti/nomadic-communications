#!/usr/bin/env python
import ConfigParser
import os
import re
import sys
import shelve
import time
import getopt
from copy import deepcopy
from parse_iperf import *

GNUPLOT = True
try:
    import Gnuplot
except ImportError, i:
    print "you will be unable to plot in real time"
    GNUPLOT = False

def interactive():
    c = Configure()
    c.make_conf()

class MenuMaker:
    """Generates a nice menu"""
    def __init__(self, choices, key = "val"):
        self.choices = choices
        self.key = key
        self.default = self.choices[0]
        self.menu = dict(enumerate(self.choices))
        
    def __str__(self):
        return '\n'.join([str(i) + ")\t" + str(self.menu[i]) for i in range(len(self.choices))])
    
    def __getitem__(self, idx):
        if self.key == "val":
            return self.menu[idx]
        elif self.key == 'idx':
            return idx
        
def menu_set(menu):
    while True:
        print str(menu)
        val = raw_input("make a choice (default %s):\n\n" % str(menu.default))
        if val == '':
            return menu.default
        else:
            try:
                return menu[int(val)]
            except KeyError:
                continue
            except ValueError:
                print "you must give integer input"
                continue
                
def search_test(shelve_file):
    pass


class Cnf:
    def __init__(self, name):
        self.conf = {}
        self.to_conf()
    
    def __str__(self):
        return ' '.join([str(val) for val in self.conf.values()])
    
    def __repr__(self):
        return str(self)

    def __getitem__(self, idx):
        return self.conf[idx]
    
    def __eq__(self, other):
        return self.conf == other.conf

    def __neq__(self, other):
        return not(self == other)

    def __sub__(self, other):
        diff = {}
        for c in self.conf.keys():
            if other.conf.has_key(c) and (self.conf[c] != other.conf[c]):
                diff[c] = self.conf[c]
        return diff

    def to_latex(self):
        """Returns a string representing the configuration in latex"""
        pass

    def to_conf(self):
        for key in self.options.keys():
            v = self.raw_conf[key]
            if type(v) == list:
                # =====================================================
                # = IMPORTANT, default value is the first in the list =
                # =====================================================
                self.conf[key] = ParamOpt(self.options[key], v[0], v)
            else:
                self.conf[key] = ConstOpt(self.options[key], v)
    
    def params(self):
        return [k for k in self.conf.keys() if isinstance(self.conf[k], ParamOpt)]
    
# ===============================================================
# = Subclasses of CNF, they only contain which options to parse =
# ===============================================================
class IperfConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        self.options = {
            "speed" : "-b",
            "host"  : "-c",
            "time"  : "-t",
            "format" :"-f",
            "interval" : "-i"
        }
        Cnf.__init__(self, "iperf")

    def __str__(self):
        return "iperf " + Cnf.__str__(self)

class ApConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        par = ["speed", "rts_threshold", "frag_threshold", "ip", "ssid", "channel", "comment"]
        # FIXME not really beatiful
        self.options = dict(zip(par, par))
        Cnf.__init__(self, "ap")

class ClientConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        par = ["speed", "brand", "model", "driver"]
        self.options = dict(zip(par, par))
        Cnf.__init__(self, "client")

class TestConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        self.options = dict(num_tests = "num_tests")
        Cnf.__init__(self, "test")


class Configure:
    conf_file = 'config.ini'
    subdir = 'test_configs'
    def __init__(self):
        self.num = 1
        self.sub_num = 1
        self.auto = ["iperf"]
        self.reader = ConfigParser.ConfigParser()
        self.reader.readfp(open(self.conf_file))
        # setting also the order in this way,
        self.conf = {
            "iperf" : IperfConf(self.get_conf("iperf")),
            "ap"    : ApConf(self.get_conf("ap")),
            "client": ClientConf(self.get_conf("client")),
            "test"  : TestConf(self.get_conf("test"))
        }
        self.sections = ParamOpt("sections", "iperf", self.conf.keys())
        # not linking, really copying the data structure
        self.lastconf = deepcopy(self.conf)

    def __str__(self):
        return '\n'.join([ (str(key) + " --> " + str(val)) for key, val in self.lastconf.items()])
            
    def __getitem__(self, idx):
        return self.conf[idx]

    def __eq__(self, other):
        return self.conf == other.conf

    def __sub__(self, other):
        """Differences from two configurations, returns a new small configuration"""
        diff = {}
        for c in self.conf.keys():
            if not(self.conf[c] == other.conf[c]):
                diff[c] = self.conf[c] - other.conf[c]
        return diff
    
    def make_config_file(self):
        """Creates a new configuration and store it"""
        while True:
            print "insert the index of the next configuration"
            self.make_conf()

    def make_conf(self):
        def conf():
            sec = menu_set(MenuMaker(self.conf.keys()))
            # only take parameters, where there is a list of possible values
            pars = tmpconf[sec].params()
            opt = menu_set(MenuMaker(pars))
            val = menu_set(MenuMaker(tmpconf[sec][opt].val_list))
            tmpconf[sec][opt].set(val)
            return False
        
        def run():
            Tester(tmpconf).run_test()
            return False

        def quit():
            print "quitting"
            return True
        
        print "starting interactive configuration"
        tmpconf = self.lastconf
        
        while True:
            print "your actual configuration is:\n%s\nChoose what you want to do:\n" % str(self)
            questions = ["Configure another parameter", "Run the test", "Quit"]
            n = menu_set(MenuMaker(questions, key = "idx"))
            if [conf, run, quit][n]():
                break
                
    def get_conf(self, section):
        conf = {}
        for k in self.reader.options(section):
            val = self.reader.get(section, k)
            if val.find(',') >= 0:  # it's a list
                conf[k] = val.replace(' ','').split(',')
            else:
                conf[k] = val
        return conf

class Plotter:
    """
        General plotter of data in array format
        maxGraphs indicates the maximum number of "functions" to be plotted
        at the same time
    """
    def __init__(self, title, value, maxGraphs = 2):
        self.title = title
        self.value = value
        self.items = []
        self.last = []
        self.maxGraphs = maxGraphs
        self.plotter = Gnuplot.Gnuplot(persist = 1)
        self.plotter.set_string("title", title)
        self.plotter.set_range('yrange', (0,"*"))
        self.plotter.set_label('xlabel', "step")
        self.plotter.set_label('ylabel', self.value)

    def add_data(self, data, name):
        """Add another data set"""
        # always keeping last maxGraphs elements in the item list and redraw them
        self.last = data
        new = Gnuplot.Data(data, title = name, with = "linespoint")
        self.items = self.items[ -self.maxGraphs + 1 : ] + [new]

    def plot(self):
        """docstring for plot"""
        self.plotter.plot(*self.items)
    
    def update(self, data):
        """Adds data to the last data set"""
        # FIXME doesn't have to redraw everything every time 
        self.last += data
        new = Gnuplot.Data(self.last, with = "linespoint", title = self.items[-1].get_option("title"))
        self.items[-1] = new
        self.plot()
    
# ==========================
# = Configuration analysis =
# ==========================
class Tester:
    def __init__(self, conf):
        """Class which encapsulates other informations about the test and run it"""
        self.conf = conf
        self.analyzer = IperfOutPlain()
        self.get_time = lambda: time.strftime("%H:%M", time.localtime())
        self.output = shelve.open("test_result")
        # self.num_tests = int(self.conf['test']['num_tests'].value)
        if self.output.has_key(str(self.conf)):
            print "careful, you've already done a test with this configuration\n: %s" %\
                str(self.conf)
        # The None values are filled before written to shelve dictionary
        self.test_conf = {
            "platform"  : os.uname(),
            "conf"      : self.conf,
            "start"     : None,
            "end"       : None,
            "result"    : None
        }
    
    def __str__(self):
        return "\n\n".join([ str(key) + ":\n" + str(val) for key, val in self.test_conf.items() ])

    def run_test(self):
        """Runs the test num_tests time and save the results"""
        cmd = str(self.conf['iperf'])
        self.test_conf["start"] = self.get_time()
        print "executing %s" % cmd
        _, w, e = os.popen3(cmd)
        for line in w.readlines():
            self.analyzer.parse_line(line)
                
        self.test_conf["end"] = self.get_time()
        self.test_conf["result"] = self.analyzer.result
        # =========================================================================
        # = IMPORTANT, if given twice the same conf it overwrites the old results =
        # =========================================================================
        self.output[str(self.conf)] = self.test_conf
        self.output.sync()
        self.output.close()
        if GNUPLOT:
            self.plotter = Plotter("testing", "kbs")
            self.plotter.add_data(self.test_conf["result"]["values"], "testing")
            self.plotter.plot()


if __name__ == '__main__':
    # TODO adding a simulation and verbosity flag
    interactive()
