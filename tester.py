#!/usr/bin/env python
# encoding: utf-8

import os
import re
import sys
import shelve
import time
import ConfigParser
from glob import glob
from getopt import getopt
from copy import deepcopy
from parse_iperf import *

GNUPLOT = True
try:
    import Gnuplot
except ImportError, i:
    print "you will be unable to plot in real time"
    GNUPLOT = False
    
dial = None
if os.path.exists('dialog.py'):
    import dialog
    dial = dialog.Dialog()
    DIALOG = True
else:
    DIALOG = False
    
CODENAME_FORMAT = r"\w\d+"
SIMULATE = False
VERBOSE = False

def clear():
    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')

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
        
# TODO Use dialog if available
def menu_set(menu):
    while True:
        print str(menu)
        val = raw_input("make a choice (default %s):\n\n" % str(menu.default))
        if val == '':
            if menu.key == "val":
                return self.default
            else:
                return 0
        else:
            try:
                return menu[int(val)]
            except KeyError:
                continue
            except ValueError:
                print "you must give integer input"
                continue

class Cnf:
    def __init__(self, name):
        self.conf = {}
        self.to_conf()
    
    # TODO Check if it's the best representation possible
    def __str__(self):
        intersect = set(self.show_opt).intersection(self.conf.keys())
        return ';\t'.join([str(self.conf[k]) for k in intersect])
    
    def __repr__(self):
        return str(self)

    def __getitem__(self, idx):
        return self.conf[idx]
    
    def __eq__(self, other):
        return self.conf == other.conf

    def __ne__(self, other):
        return not(self == other)

    def __add__(self, other):
        merged = deepcopy(self)
        merged.conf.update(other.conf)
        return merged

    def __sub__(self, other):
        """ Getting the diff of two configuration"""
        subt = deepcopy(self)
        for key, val in subt.conf.items():
            if other.conf.has_key(key):
                if other.conf[key] == subt.conf[key]:
                    subt.conf.pop(key)
                else:
                    subt.conf[key] = other.conf[key]
        return subt

    def __getitem__(self, idx):
        try:
            return self.conf[idx].value
        except KeyError:
            print "key %s does not exist" % str(idx)

    def keys(self):
        return self.conf.iterkeys()
    
    def is_empty(self):
        return self.conf == {}
    
    def issubset(self, other):
        return set(self.conf.keys()).issubset(other.conf.keys())
    
    def to_min(self):
        """Gets the minimal Cnf, without choices and taking off null values"""
        not_nulls = filter(lambda x: self.conf[x].value != '', self.conf.keys())
        return dict(zip(not_nulls, [self.conf[key] for key in not_nulls]))

    def to_latex(self):
        """Returns a string representing the configuration in latex"""
        pass

    def to_conf(self):
        for key in self.raw_conf.keys():
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

# TODO clean those multiple useless classes
class IperfConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        self.options = {
            "host"  : "-c",
            "speed" : "-b",
            "time"  : "-t",
            "format" :"-f",
            "interval" : "-i"
        }
        Cnf.__init__(self, "iperf")

    def __str__(self):
        res = ""
        # CHANGED in this way I'm safe that I always have the right order
        for o in self.options.keys():
            if self.conf.has_key(o):
                res += str(self.conf[o]) + " "
        return "iperf " + res.rstrip() # take off last space, pretty ugly

class ApConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        par = ["mode", "speed", "rts_threshold", "frag_threshold", "ip", "ssid",
                "channel", "comment", "firmware", "model"]
        # FIXME not really beatiful
        self.options = dict(zip(par, par))
        self.show_opt = ["mode", "speed", "rts_threshold", "frag_threshold"]
        Cnf.__init__(self, "ap")

class ClientConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        par = ["speed", "brand", "model", "driver"]
        self.options = dict(zip(par, par))
        self.show_opt = ["speed"]
        Cnf.__init__(self, "client")

# CHANGED I had to pull opt_conf outside to let shelve pickle work
opt_conf = {
    "iperf" : lambda x: IperfConf(x),
    "ap"    : lambda x: ApConf(x),
    "client": lambda x: ClientConf(x),
}

class Configuration:
    """Class of a test configuration, only contains a one-one dict and a codename
    The value of the dict can be whatever, even a more complex thing.
    This is the basic type we're working on.
    The configuration is always kept as complete, in the sense that it also keeps
    all the possible alternatives, to_min will output a minimal dictionary representing
    the default values"""

    def __init__(self, conf_file, codename = ""): #CHANGED codename only given by ini_file
        self.conf = {}
        # TODO use the default method passing when creating the dict
        self.reader = ConfigParser.ConfigParser()
        self.conf_file = conf_file
        self.from_ini(open(conf_file))      # directly creating from __init__
        self.codename = codename
        
    def __str__(self):
        return '\n'.join(["%s:\t %s" % (str(k), str(v)) for k, v in self.conf.items()])
        
    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.conf == other.conf

    def __getitem__(self, idx):
        try:
            return self.conf[idx]
        except KeyError:
            return None

    def __setitem__(self, idx, val):
        self.conf[idx] = val     

    def __sub__(self, other):
        diff = deepcopy(self)
        for key in diff.conf.keys():
            if other.conf.has_key(key):
                diff.conf[key] -= other.conf[key]
                # CHANGED added this check to avoid empty keys
                if diff.conf[key].is_empty():
                    diff.conf.pop(key)
        diff.codename = other.codename
        return diff
        
    def __add__(self, other):
        """Merge two configurations, the second one has the last word
        Note that of course this IS NOT symmetric"""
        merged = deepcopy(self)
        for key in opt_conf.keys():
            if merged.conf.has_key(key) and other.conf.has_key(key):
                merged.conf[key] += other.conf[key]
            elif other.conf.has_key(key):
                merged.conf[key] = other.conf[key]
        merged.codename = other.codename
        return merged

    def to_min(self):
        # creating a new dictionary automatically minimizing values
        return dict(zip(self.conf.keys(), map(lambda x: x.to_min(), self.conf.values())))
    
    def _write_conf(self, conf_file):
        """Write the configuration in ini format
        after having minimized it"""
        writer = ConfigParser.ConfigParser()
        conf = self.to_min()
        for sec, opt in conf.items():
            writer.add_section(sec)
            for key, val in opt.items():
                writer.set(sec, key, val.value)
        writer.write(conf_file)

    def keys(self):
        return self.conf.iterkeys()
                    
    def from_ini(self, conf_file):
        """Takes a configuration from ini"""
        self.reader.readfp(conf_file)
        for sec in self.reader.sections():
            tmpconf = {}
            for opt in self.reader.options(sec):
                val = self.reader.get(sec, opt)
                if val.find(',') >= 0:
                    tmpconf[opt] = val.replace(' ', '').split(',')
                else:
                    tmpconf[opt] = val
            try:
                self.conf[sec] = opt_conf[sec](tmpconf)
            except KeyError:
                print "section %s not existing, skipping it" % sec
        
    def to_ini(self, ini_file):
        self._write_conf(ini_file)
        
    def show(self):
        head = "#*** test %s ***" % self.codename
        tail = "#--- end test %s ---\n\n" % self.codename
        print head.center(40)
        self.to_ini(sys.stdout)
        print tail.center(40)


class TestBattery:
    def __init__(self):
        # setting also the order in this way,
        self.conf_file = "config.ini"
        self.default_conf = Configuration(self.conf_file, codename = "default")
        self.auto = set(["iperf"])
        # maybe use "sets" to avoid duplicates
        self.conf_dir = "configs"
        # list of all possible tests stored
        self.test_configs = filter(lambda x: re.search("\w\d+", x), glob(os.path.join(self.conf_dir, '*ini')))
        self.battery = []

    def _group_auto(self):
        """Groups configuration in a way such that human
        intervent is as minumum"""
        # CHANGED using new - and + overloaded operators
        def eql(t1, t2):
            changed = set((t1 - t2).conf.keys())
            return changed.issubset(self.auto)
        groups = []
        for test in self.battery:
            added = False
            for i in range(len(groups)):
                # at position 0 we have the testimonial
                if eql(test, groups[i][0]):
                    groups[i].append(test)
                    added = True
                    break
            if not(added):
                groups.append([test])
        return groups

    def is_consistent(self, conf):
        """Checking if configuration loaded is consistent with default configuration"""
        for sec in conf.keys():
            if sec not in self.default_conf.keys():
                print "section %s not found, skipping it" % str(sec)
            else:
                for opt in conf[sec].keys():
                    if opt not in self.default_conf[sec].keys():
                        print "option %s not found, skipping it" % str(opt)
                    else:
                        param = self.default_conf[sec].conf[opt]
                        if not(param.valid(conf[sec].conf[opt].value)):
                            print "option %s not valid %s \n" % (opt, param.choices())
                            return False
        return True
    
    def load_conf(self, conf_file):
        """Loads a configuration from conf_file merging it with
        the default configuration"""
        # the codename is given from the conf_file
        cnf = Configuration(conf_file, codename = re.search(r"\w\d+", conf_file).group())
        if self.is_consistent(cnf):
            merged = self.default_conf + cnf
            if merged in self.battery:
                print "you have already loaded the configuration in %s, not adding" % conf_file
            else:
                print "adding configuration in %s" % conf_file
                self.battery.append(merged)
        else:
            print "error in %s, please correct the values" % conf_file

    def load_configs(self):
        for conf in self.test_configs:
            self.load_conf(conf)
    
    def run(self):
        """Start the tests, after having sorted them"""
        CONF = "\n\nconfiguration -> \n %s\n"
        def sub_run(tests):
            raw_input("check configuration of parameters before starting the automatic tests, press enter when done \n")
            clear()
            for test_conf in tests:
                Tester(test_conf).run_test()
            
        groups = self._group_auto()
        first = groups[0]
        print CONF % first[0]
        sub_run(first)
        for i in range(1, len(groups)):
            # in this way we only show the difference from the last group
            # of tests
            print CONF % (groups[i][0] - groups[i-1][0])
            sub_run(groups[i])
    
    def show_tests(self):
        for test in self.battery:
            test.show()
    
    def batch(self):
        self.load_configs()
        self.run()


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
        self.get_time = lambda: time.strftime("%d-%m-%y_%H:%M", time.localtime())
        self.output = shelve.open("test_result")
        self.iperf_out_file = os.path.join("iperf_out", "iperf_out" + self.conf.codename + ".txt")
        # The None values are surely rewritten before written to shelve dictionary
        self.test_conf = {
            "platform"  : os.uname(),
            "conf"      : self.conf,
            "start"     : None,
            "end"       : None,
            "result"    : None
        }
    
    def run_test(self):
        """Runs the test num_tests time and save the results"""
        cmd = str(self.conf['iperf'])
        self.test_conf["start"] = self.get_time()
        # TODO insert a test to verify if the host is responding
        if SIMULATE:
            print "only simulating execution"
        else:
            print "executing %s" % cmd
            print "also writing output to %s" % self.iperf_out_file
            _, w, e = os.popen3(cmd)
            out_file = open(self.iperf_out_file, 'w')
            for line in w.readlines():
                out_file.write(line)      # writing iperf output also to file (to double check results)
                self.analyzer.parse_line(line)
            out_file.close()
        
            self.test_conf["end"] = self.get_time()
            self.test_conf["result"] = self.analyzer.result
            # =========================================================================
            # = IMPORTANT, if given twice the same conf it overwrites the old results =
            # =========================================================================
            self.output[str(self.conf)] = self.test_conf
            self.output.close()
            if GNUPLOT:
                self.plotter = Plotter("testing", "kbs")
                self.plotter.add_data(self.test_conf["result"]["values"], self.conf.codename)
                self.plotter.plot()        

if __name__ == '__main__':
    opts, args = getopt(sys.argv[1:], 'vs', ['verbose', 'simulate'])
    for o, a in opts:
        if o in ('-v', '--verbose'):
            VERBOSE = True
        if o in ('-s', '--simulate'):
            SIMULATE = True
    # we can pass as many configs files as you want or just let
    # the program look for them automatically
    if args:
        t = TestBattery()
        for conf_file in args:
            t.load_conf(conf_file)
            t.run()
    else:
        TestBattery().batch()
