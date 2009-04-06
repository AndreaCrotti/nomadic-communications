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
from src.parse_iperf import *
from src.config import *
from src.utils import *
from src.opts import *

GNUPLOT = True
try:
    import Gnuplot
except ImportError, i:
    print "you will be unable to plot in real time"
    GNUPLOT = False
    
# global flags
SIMULATE = False
VERBOSE = False

# exit codes
BADHOST = 1
BADCONF = 2

# template strings parametric constants
CODENAME_FORMAT = r"\d\w"
USER_CONFS = "userconfs/%s.ini"
IPERF_OUT = "iperf_out/iperf_out_%s.txt"
CONFIGS = "configs/test_%s.ini"
DUMPS = "analysis/traffic/dump_%s.out"
RESULTS = "test_result_%s"

class TestBattery:
    def __init__(self, username):
        try:
            # maybe need to close also somewhere
            self.conf_file = "default.ini"
        except IOError:
            print "unable to found default configuration, quitting"
            sys.exit(BADCONF)
        
        else:
            self.default_conf = Configuration(self.conf_file, codename = "default")
            self.username = username
            self.user_conf = Configuration(USER_CONFS % self.username)
            # This default configuration is only used the first time
            self.conf = self.default_conf + self.user_conf
            self.auto = set(["iperf"])
            # list of all possible configs stored, better not opening directly here
            self.test_configs = filter(lambda x: re.search(CODENAME_FORMAT, x), glob(CONFIGS % "*"))
            self.battery = []

    def _group_auto(self):
        """Groups configuration in a way such that intervent is minumum"""
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
            if sec not in self.conf.keys():
                print "section %s not found, skipping it" % str(sec)
            else:
                for opt in conf[sec].keys():
                    if opt not in self.conf[sec].keys():
                        print "option %s not found, skipping it" % str(opt)
                    else:
                        param = self.conf[sec].conf[opt]
                        if not(param.valid(conf[sec].conf[opt].value)):
                            print "option %s not valid %s \n" % (opt, param.choices())
                            return False
        return True
    
    def load_conf(self, conf_file, codename):
        """Loads a configuration from conf_file merging it with
        the default configuration"""
        # the codename is given from the conf_file
        cnf = Configuration(conf_file, codename)
        if self.is_consistent(cnf):
            merged = self.conf + cnf
            if merged in self.battery:
                print "you have already loaded the configuration in %s, not adding" % conf_file
            else:
                print "adding configuration in %s" % conf_file
                self.battery.append(merged)
        else:
            print "error in %s, please correct the values" % conf_file

    def load_configs(self):
        for conf in self.test_configs:
            codename = re.search(CODENAME_FORMAT, conf).group()
            self.load_conf(conf, codename)
    
    def run(self):
        """Start the tests, after having sorted them"""
        CONF = "\n\nconfiguration -> \n %s\n"
            # TODO change the name of this file in relation to user_conf loaded
        SHOUT = shelve.open(RESULTS % self.username)
        def sub_run(tests):
            raw_input("check configuration of parameters before starting the automatic tests, press enter when done \n")
            i = 0
            # CHANGED added a very nice control over possible signals
            while i < len(tests):
                clear()
                print CONF % str(tests[i])
                if SIMULATE:
                    print "only simulating execution of %s\n\n" % str(tests[i]['iperf'])
                    # raw_input("press input to see next test")
                    i += 1
                else:
                    # TODO launch the tcpdump command if monitor set
                    try:
                        key, val = Tester(tests[i]).run_test()
                    except KeyboardInterrupt:
                        a = raw_input("last test canceled, (s)kip or (r)estart or (q)uit the test session")
                        if a == 'q':
                            sys.exit(0)
                        elif a == 's':
                            i += 1
                        # not increasing we automatically stay in the same test (default behaviour)
                    else:
                        if SHOUT.has_key(key):
                            a = raw_input("you are overwriting test % s, are you sure (y/n)" % key)
                            if a == 'y':
                                print "test %s overwritten " % key
                                SHOUT[key] = val
                                SHOUT.sync()
                        else:
                            SHOUT[key] = val
                        i += 1
        
        groups = self._group_auto()
        if not groups:
            print "no configurations loaded, quitting"
            sys.exit(BADCONF)

        first = groups[0]
        print CONF % first[0]
        sub_run(first)
        for i in range(1, len(groups)):
            # print CONF % (groups[i][0] - groups[i-1][0])
            sub_run(groups[i])
        SHOUT.close()
    
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
        self.iperf_out_file = IPERF_OUT % self.conf.codename
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
        print "\t TEST %s:\n" % self.conf.codename
        print "executing %s" % cmd
        print "also writing output to %s" % self.iperf_out_file
        _, w, e = os.popen3(cmd)
        # with this line we check if the host is responding or not
        if re.search("did not receive ack", e.read()):
            print "host %s not responding, quitting the test" % self.conf['iperf']['host']
            sys.exit(BADHOST)
        
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
        
        if GNUPLOT:
            self.plotter = Plotter("testing", "kbs")
            self.plotter.add_data(self.test_conf["result"]["values"], self.conf.codename)
            self.plotter.plot()

        return self.conf.codename, self.test_conf

def usage():
    print """
    ./tester.py [-s|--simulate] <user> <conf1> <conf2>...
    if no file are given in input it loads the configuration files "configs/test_\d\w.ini
    user is mandatory and will pick up the configuration from userconfs/*.ini
    """
    sys.exit(0)


if __name__ == '__main__':
    # TODO check input from stdin (fake file better than StringIO)
    # TODO use optparse instead, much more flexible
    opts, args = getopt(sys.argv[1:], 'vsh', ['verbose', 'simulate', 'help'])
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        if o in ('-v', '--verbose'):
            VERBOSE = True
        if o in ('-s', '--simulate'):
            SIMULATE = True

    # we can pass as many configs files as you want or just let
    # the program look for them automatically
    if args:
        name = args[0]
        if not(os.path.exists(USER_CONFS % name)):
            print "no configuration for %s" % name
            sys.exit(BADCONF)
        else:
            t = TestBattery(name)
            if args[1:]:
                for conf_file in args[1:]:  # all the others could be conf
                    t.load_conf(conf_file, "abc")
                    t.run()
            else:
                t.batch()
    else:
        usage()