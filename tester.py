#!/usr/bin/env python
import os
import re
import sys
import shelve
import time
import ConfigParser
from copy import deepcopy
from parse_iperf import *

GNUPLOT = True
try:
    import Gnuplot
except ImportError, i:
    print "you will be unable to plot in real time"
    GNUPLOT = False
    
if os.path.exists('dialog.py'):
    import dialog
    DIALOG = True
else:
    DIALOG = False

def interactive():
    t = TestBattery()
    t.interactive()

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

class ConfigReader:
    def __init__(self, conf_file):
        self.conf_file = conf_file
        self.reader = ConfigParser.ConfigParser()
        # handle exception
        self.reader.readfp(open(self.conf_file))
                
    def get_conf(self, section):
        conf = {}
        for k in self.reader.options(section):
            val = self.reader.get(section, k)
            if val.find(',') >= 0:  # it's a list
                conf[k] = val.replace(' ','').split(',')
            else:
                conf[k] = val
        return conf

class ConfigWriter:
    def __init__(self, conf_file):
        self.conf_file = conf_file
        self.writer = ConfigParser.ConfigParser()
        
    def write_conf(self, conf):
        for sec, opts in conf.items():
            self.writer.add_section(sec)
            for key, val in opts.conf.items():
                self.writer.set(sec, key, val)
        self.writer.write(self.conf_file)
        


class TestBattery:
    def __init__(self):
        # setting also the order in this way,
        self.conf_file = "config.ini"
        self.conf_reader = ConfigReader("config.ini")
        self.auto = ["iperf"]
        # maybe use "sets" to avoid duplicates
        self.conf_dir = "configs"
        self.battery = []
        self.full = {
            "iperf" : IperfConf(self.conf_reader.get_conf("iperf")),
            "ap"    : ApConf(self.conf_reader.get_conf("ap")),
            "client": ClientConf(self.conf_reader.get_conf("client")),
            "test"  : TestConf(self.conf_reader.get_conf("test"))
        }
        # taking a minimal conf, which is actually the real default in this moment
        self.last_conf = deepcopy(self.full)

    def _group_auto(self):
        def eql(t1, t2):
            changed = (t1 - t2).keys()
            for c in changed:
                if c not in self.auto:
                    return False
            return True
            
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
    
    def conf(self):
        # starting to create a new battery of test
        cnf = Configure(self.last_conf)
        cnf.make_conf()
        self.battery.append(cnf)
        self.last_conf = cnf.conf
        return False
    
    def run(self):
        """Start the tests, after having sorted them"""
        print "running the test"
        groups = self._group_auto()
        for sub in groups:
            print "configuration -> \n %s\n" % sub[0]
            raw_input("check configuration of parameters before starting the automatic tests, press enter when done \n")
            for test_conf in sub:
                Tester(test_conf).run_test()
        # when the tests are done we also want to save the configurations
        self.store_configs()
        return True
    
    def show_test(self):
        for test in self.battery:
            test.show()
        return False
    
    def store_configs(self):
        for cnf in self.battery:
            write_conf(to_min(cnf), open(os.path.join(self.conf_dir, cnf.codename)), 'w')
        return True
    
    def interactive(self):
        """Configure the test battery"""
        questions = ["create a new test", "show the tests", "run the tests", "store configurations and exit"]
        while True:
            n = menu_set(MenuMaker(questions, key = "idx"))
            if [self.conf, self.show_test, self.run, self.store_configs][n]():
                break


class Configure:
    def __init__(self, full_conf):
        """The input of Configure is a total configuration and a minimal (default)
        configuration"""
        self.full_conf = full_conf
        # at the end of the configuration this will be a minimal configuration
        self.conf = deepcopy(self.full_conf)
        self.codename = ""

    def __str__(self):
        return '\n'.join([ (str(key) + " --> " + str(val)) for key, val in self.conf.items()])
            
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

    def show(self):
        print "\n"
        head = "*** test %s ***" % self.codename
        tail = "--- end test %s ---\n\n" % self.codename
        print head.center(40)
        write_conf(to_min(self.conf), sys.stdout)
        print tail.center(40)
        return False

    def configure(self):
        sec = menu_set(MenuMaker(self.full_conf.keys()))
        # only take parameters, where there is a list of possible values
        pars = self.full_conf[sec].params()
        opt = menu_set(MenuMaker(pars))
        val = menu_set(MenuMaker(self.full_conf[sec][opt].val_list))
        self.conf[sec][opt].set(val)
        return False

    def quit(self):
        print "quitting"
        return True

    def make_conf(self):
        self.codename = raw_input("insert name of this test:\n")
        questions = ["Configure a parameter", "Show current configuration", "Quit"]
        while True:
            print "your actual configuration is:\n%s\nChoose what you want to do:\n" % str(self)
            n = menu_set(MenuMaker(questions, key = "idx"))
            if [self.configure, self.show, self.quit][n]():
                break


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


def to_min(full_conf):
    conf = {}
    for key,val in full_conf.items():
        conf[key] = {}
        for opt, value in val.conf.items():
            conf[key][opt] = value.value
    return conf
        
def write_conf(conf, conf_file):
    writer = ConfigParser.ConfigParser()
    for key, val in conf.items():
        writer.add_section(key)
        for k, v in val.items():
            writer.set(key, k, v)
    writer.write(conf_file)
    

if __name__ == '__main__':
    # TODO adding a simulation and verbosity flag
    interactive()
