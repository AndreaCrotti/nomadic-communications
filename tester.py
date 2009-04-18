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
from src.vars import *

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

def get_res(root, code):
    paths = [ os.path.join(root, k, val % code) for k, val in RESULTS.iteritems() ]
    return dict(zip(RESULTS.keys(), paths))

def banner(text, sym="*"):
    start = end = sym * 40
    print "\n".join(map(lambda x: x.center(50), [start, text, end]))

class TestBattery:
    def __init__(self, username):
        try:
            # maybe need to close also somewhere
            self.conf_file = "default.ini"
        except IOError:
            print "unable to found default configuration, quitting"
            sys.exit(BADCONF)

        self.default_conf = Configuration(self.conf_file, codename = "default")
        self.user_conf = Configuration(USER_CONFS % self.username, codename = username)
        self.monitor = False
        if self.user_conf["monitor"]["ssh"]:
            self.ssh = self.user_conf["monitor"]["ssh"]
            self.monitor = True
        # monitoring informations must stay in user_conf
        self.conf = self.default_conf + self.user_conf
        self.conf.username = "merged"
        # list of all possible configs stored, not opening directly here
        self.test_configs = glob(CONFIGS % "*")
        self.battery = []
        # dictionary containing absolute paths for the results
        self.analyzer = IperfOutPlain()
        self.root = ROOT % username

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

    def load_configs(self, configs = []):
        name = lambda x: re.search(r"configs/(.*?).ini", x).groups()[0]
        if not configs:
            configs = self.test_configs
        for conf in configs:
            codename = name(conf)
            self.load_conf(conf, codename)
    
    def summary(self):
        """Prints the summary of the tests that we will execute"""
        for i in range(len(self.battery)):
            banner(str(i) + "):\t" + self.battery[i].codename)
            print "\n"

    def make_subtree(self, root, dirs):
        if not os.path.exists(root):
            os.mkdir(root)
            for d in dirs:
                os.mkdir(os.path.join(root, d))
            # creating a new empty file
            open(os.path.join(root, COMPLETED), 'w')

    def pre_run(self):
        self.make_subtree(self.root, RESULTS.iterkeys())
        compl_file = os.path.join(self.root, COMPLETED)
        try:
            compl = map(lambda x: "configs/" + x + ".ini", open(compl_file).read().splitlines())
        except IOError:
            # if the file is not there creates it and loads everything
            open(compl_file, 'w')
            self.load_configs()
        else:
            diff = list(set(self.test_configs).difference(compl))
            diff.sort()
            # I only load the configs I want to
            self.load_configs(diff)
            self.summary()

    def run(self):
        # TODO battery and _group_auto can be reimplemented using itertools.groupby
        i = 0
        while i < len(self.battery):
            if SIMULATE:
                print "only simulating %s" % str(self.battery[i])
                i += 1
                continue
            banner("TEST %s:\n" % self.battery[i].codename, sym="=")
            try:
                # better handle it here not inside the test itself
                self.run_test(self.battery[i])
            except KeyboardInterrupt:
                a = raw_input("last test canceled, (s)kip or (r)estart or (q)uit the test session:\n")
                if a == 'q':
                    sys.exit(0)
                elif a == 's':
                    i += 1
            else:
                print "writing the results to files"
                self.write_results(self.battery[i])
                print "test %s done" % self.battery[i].codename
                i += 1

    def run_test(self, test):
        """
        Running one single test, plotting the results if gnuplot availble
        and saving the results in a directory structure
        """
        print test
        cmd = str(test['iperf'])
        raw_input("Press any key when ready:\n")
        # automatically writes the output to the right place, kind of magic of subprocess
        if self.monitor:
            mon = subprocess.Popen(self.ssh % "dump.tmp", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            raw_input("unable to monitor, you have to do it yourself, press a key when ready to sniff")
        
        print "executing %s" % cmd
        proc = subprocess.Popen(cmd, shell=True, stdout=open("iperf.tmp",'w'), stderr=subprocess.PIPE)
        if re.search("did not receive ack", proc.stderr.read()):
            print "host %s not responding, quitting the test" % self.conf['iperf']['host']
            sys.exit(BADHOST)
    
    def write_results(self, test):
        """Finally writes the results of the test in the right directories"""
        res_dict = get_res(self.root, test.codename)
        # saving the dump file
        shutil.move("dump.tmp", res_dict["dump"])
        shutil.move("iperf.tmp", res_dict["iperf"])
        self.analyzer.parse_file(open(res_dict["iperf"], 'r'))
        test.to_ini(open(res_dict["full_conf"], 'w'))
        self.plot(self.analyzer.result['values'], test.codename, res_dict["graphs"])
        open(os.path.join(self.root, COMPLETED), 'a').write(test.codename + "\n")

    def plot(self, results, codename, filename):
        """Plots and writes the graph generated to filename"""
        plotter = Plotter("testing", "kbs")
        plotter.add_data(results, codename)
        plotter.plot()
        plotter.save(filename)

    def batch(self):
        """Automatic run of the tests"""
        self.pre_run()
        self.run()


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
    

def usage():
    print """
    ./tester.py [-s|--simulate] <user> <conf1> <conf2>...
    if no file are given in input it loads the configuration files "configs/test_\d\w.ini
    user is mandatory and will pick up the configuration from userconfs/*.ini
    """
    sys.exit(0)


if __name__ == '__main__':
    # TODO implementing a test cleaner
    opts, args = getopt(sys.argv[1:], 'cvsh', ['verbose', 'simulate', 'help', 'clean'])
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
                    # FIXME ugly hardcoding of file path
                    t.load_conf(conf_file, conf_file.split(".")[0].split("/")[1])
                t.run()
            else:
                t.batch()
    else:
        usage()