#!/usr/bin/env python
# encoding: utf-8

import os
import re
import sys
import shelve
import time
import ConfigParser
import subprocess
import shutil

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
USER_CONFS = "userconfs/%s.ini"
CONFIGS = "configs/%s.ini"
RESULTS = "test_result_%s"
MESSAGE = "media/message.wav"

PATH_DIC = {
    "root"      : "results_%(user)s",
    "sub": {
        "full_conf" : "full_%(code)s.ini",
        "dump"      : "dump_%(code)s.out",
        "iperf"     : "iperf_out_%(code)s.txt"
    }
}

def banner(text, sym="*"):
    start = sym * 40
    end = start
    print "\n".join(map(lambda x: x.center(50), [start, text, end]))

def get_path(vars, v):
    if v == "root":
        return PATH_DIC[v] % vars
    else:
        return os.path.join(PATH_DIC["root"], PATH_DIC[v]) % vars

class TestBattery:
    def __init__(self, username):
        try:
            # maybe need to close also somewhere
            self.conf_file = "default.ini"
        except IOError:
            print "unable to found default configuration, quitting"
            sys.exit(BADCONF)

        self.default_conf = Configuration(self.conf_file, codename = "default")
        self.username = username
        self.user_conf = Configuration(USER_CONFS % self.username, codename = self.username)
        self.ssh, self.scp = None, None
        # monitoring informations must stay in user_conf
        try:
            self.ssh = self.user_conf["monitor"]["ssh"]
            self.scp = self.user_conf["monitor"]["scp"]
        except KeyError:
            print "unable to automatically start the monitor node, do it manually"
        # This default configuration is only used the first time FIXME not nice
        self.conf = self.default_conf + self.user_conf
        self.conf.username = "merged"
        # set of automatically maneageble settings
        self.auto = set(["iperf"])
        # list of all possible configs stored, not opening directly here
        self.test_configs = glob(CONFIGS % "*")
        self.battery = []
        # dictionary containing absolute paths for the results
        self.analyzer = IperfOutPlain()
        self.paths = {}

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
                        # TODO add a sanity check for consistency checking over the merged conf
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
            if merged in self.battery:      # this works only if == defined correctly
                print "you have already loaded the configuration in %s, not adding" % conf_file
            else:
                print "adding configuration in %s" % conf_file
                self.battery.append(merged)
        else:
            print "error in %s, please correct the values" % conf_file

    def load_configs(self):
        for conf in self.test_configs:
            codename = re.search(r"configs/(.*?).ini", conf).groups()[0]
            self.load_conf(conf, codename)
    
    def summary(self):
        """Prints the summary of the tests that we will execute"""
        # FIXME two calls to _group_auto not necessary
        groups = self._group_auto()
        for i in range(len(groups)):
            print "GROUP NUMBER %d:\n" % i
            for j in range(len(groups[i])):
                print "\t\tTEST %s" % groups[i][j].codename
                print "test %d:\n%s" % (j, str(groups[i][j]))
            print "\n"

    def make_tree(self):
        """Creates the basic emtpy tree"""
        self.root = PATH_DIC["root"] % {"user" : self.username}
        try:
            os.mkdir(self.root)
        except OSError:
            print "%s Already existing moving old result folder" % self.root
            if os.path.exists(self.root + ".old"):
                shutil.rmtree(self.root + ".old")
            shutil.move(self.root, self.root + ".old")
            os.mkdir(self.root)
        for sub in PATH_DIC["sub"].iterkeys():
            path = os.path.join(self.root, sub)
            os.mkdir(path)
            self.paths[sub] = os.path.join(path, PATH_DIC["sub"][sub])

    def run(self):
        self.make_tree()
        self.summary()
        groups = self._group_auto()
        if not(groups):
            print "no configuration loaded, quitting"
            sys.exit(BADCONF)
        else:
            for battery in groups:
                print "\n\n"
                if SIMULATE:
                    print "only simulating execution of %s" % str(battery[0]['iperf'])
                    raw_input("see next configuration:\n")
                else:
                    
                    banner("STARTING BATTERY")
                    self.run_battery(battery)
                    # play(MESSAGE)

    def run_battery(self, battery):
        """Running a test battery, catching KeyboardInterrupts in the middle"""
        print str(battery[0])
        raw_input("starting test battery, check non automatic parameters:\n")
        i = 0
        while i < len(battery):
            # CHANGED not clearing because on xterm deletes the "history"
            # clear()
            # CHANGED added a very nice control over possible signals
            try:
                self.run_test(battery[i])
            except KeyboardInterrupt:
                a = raw_input("last test canceled, (s)kip or (r)estart or (q)uit the test session:\n")
                if a == 'q':
                    sys.exit(0)
                elif a == 's':
                    i += 1
                # not increasing we automatically stay in the same test (default behaviour)
            else:
                i += 1

    def run_test(self, test):
        """Running one single test"""
        d = dict(code=test.codename)
        iperf_out = open(self.paths["iperf"] % d, 'w')
        # saving full configuration
        test.to_ini(open(self.paths["full_conf"] % d, 'w'))
        banner("TEST %s:\n" % test.codename, sym="=")
        print str(test)
        cmd = str(test['iperf'])
        if self.ssh:
            subprocess.Popen(self.ssh, shell=True, stdout=subprocess.PIPE)
        # running the command
        print "running %s, also writing to %s" % (cmd, iperf_out.name)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if re.search("did not receive ack", proc.stderr.read()):
            print "host %s not responding, quitting the test" % self.conf['iperf']['host']
            sys.exit(BADHOST)

        for line in proc.stdout.xreadlines():
            self.analyzer.parse_line(line)
            iperf_out.write(line)
        iperf_out.close()
        
        if self.scp:
            # leaving stderr to stdout for debugging purposes
            subprocess.Popen(self.scp, shell=True, stdout=subprocess.PIPE).wait()
            shutil.move("out", self.paths["dump"] % d)
        
        if GNUPLOT:
            plotter = Plotter("testing", "kbs")
            plotter.add_data(self.analyzer.result['values'], test.codename)
            plotter.plot()
    
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
        new = Gnuplot.Data(data, title = name)
        self.items = self.items[ -self.maxGraphs + 1 : ] + [new]

    def plot(self):
        """docstring for plot"""
        self.plotter.plot(*self.items)
    
    # def update(self, data):
    #     """Adds data to the last data set"""
    #     # FIXME doesn't have to redraw everything every time
    #     self.last += data
    #     new = Gnuplot.Data(self.last, title = self.items[-1].get_option("title"))
    #     self.items[-1] = new
    #     self.plot()
    

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
                    t.load_conf(conf_file, conf_file.split(".")[0].split("/")[1])
                    t.run()
            else:
                t.batch()
    else:
        usage()