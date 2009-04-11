import re
import sys
import ConfigParser
from copy import deepcopy
# TODO must take off this
from opts import *
from tester import *

class Cnf:
    def __init__(self, name):
        self.conf = {}
        self.to_conf()
        # setting the complementar, all options which are not normally shown
        try:
            getattr(self, "show_opt")
        except AttributeError:
            self.show_opt = list(set(self.conf.keys()))
            self.non_show_opt = []
        else:
            self.non_show_opt = list(set(self.conf.keys()) - set(self.show_opt))
    
    # TODO Check if it's the best representation possible
    def __str__(self):
        intersect = set(self.show_opt).intersection(self.conf.keys())
        return ';\t'.join([str(self.conf[k]) for k in intersect])
    
    def __repr__(self):
        return str(self)

    # FIXME enough consistent?
    def __getitem__(self, idx):
        return self.conf[idx]
    
    def __eq__(self, other):
        return self.conf == other.conf

    def __ne__(self, other):
        return not(self == other)

    # TODO adding a check to see if null value in the second?
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
            elif v in ('True', 'False'):
                if v == 'True':
                    self.conf[key] = ConstOpt(self.options[key], "") # TODO check if better BoolOpt
            else:
                self.conf[key] = ConstOpt(self.options[key], v)
    
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
            "interval" : "-i",
            "udp"   : "-u"
        }
        self.show_opt = ["host", "udp", "speed", "time", "interval", "format"]
        Cnf.__init__(self, "iperf")

    def __str__(self):
        res = ""
        # CHANGED finally fixed ordering of options in iperf
        for o in self.show_opt:
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
        par = ["speed", "brand", "rts_threshold", "frag_threshold", "model", "driver"]
        self.options = dict(zip(par, par))
        self.show_opt = ["speed", "rts_threshold", "frag_threshold"]
        Cnf.__init__(self, "client")
        
class MonitorConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        par = ["host", "interface"]
        self.options = dict(zip(par, par))
        self.ssh = None
        self.scp = None
        Cnf.__init__(self, "monitor")
        if self.conf['host'] and self.conf['interface']:
            self.ssh = " ".join(["ssh", self.conf['host'].value,  "tcpdump -i", self.conf['interface'].value]) + " %s"
            self.scp = " ".join(["scp", self.conf['host'].value + ":%s "]) + "%s"
        
    def __str__(self):
        return "\n".join([self.ssh % ("options"), self.scp % ("remote", "local")])
        
class GnuplotConf(Cnf):
    def __init__(self, conf):
        """Handling gnuplot configuration"""
        self.raw_conf = conf
        par = ["style", "lineswidth"]
        self.options = dict(zip(par, par))
        Cnf.__init__(self, "gnuplot")


# CHANGED I had to pull opt_conf outside to let shelve pickle work
opt_conf = {
    "iperf" : lambda x: IperfConf(x),
    "ap"    : lambda x: ApConf(x),
    "client": lambda x: ClientConf(x),
    "monitor": lambda x: MonitorConf(x),
    "gnuplot": lambda x: GnuplotConf(x)
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
        """Substraction between configuration, equal values are eliminated"""
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
        """Returns a new dictionary with only not null keys"""
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
                if re.search(r"\S", val):       # CHANGED only getting non null values \S is not blank
                    if val.find(',') >= 0:
                        tmpconf[opt] = val.replace(' ', '').split(',')
                    # if a wider range is given
                    elif val.find('..') >= 0:
                        try:
                            st = val.split('..')
                            start, end = int(st[0]), int(st[1])
                        except ValueError:
                            print "a range must be of integers"
                        else:
                            if start >= end:
                                print "nonsense range"
                            else:
                                tmpconf[opt] = range(start, end)
                    else:
                        tmpconf[opt] = val
            try:
                self.conf[sec] = opt_conf[sec](tmpconf)
            except KeyError:
                print "section %s not existing, skipping it" % sec
        conf_file.close()
        
    def to_ini(self, ini_file):
        self._write_conf(ini_file)
        
    def show(self):
        head = "#*** test %s ***" % self.codename
        tail = "#--- end test %s ---\n\n" % self.codename
        print head.center(40)
        self.to_ini(sys.stdout)
        print tail.center(40)
