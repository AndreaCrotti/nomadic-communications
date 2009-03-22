#!/usr/bin/env python
import re
import doctest
import Gnuplot
import sys
import time
import shelve
import os
import ConfigParser
import copy

class IperfOutput(object):
    """class to handle iperf outputs in different formats
        possible input formats are this (PLAIN):
        [  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)
        or the csv mode (CSV):
        20090314193213,172.16.201.1,63132,172.16.201.131,5001,3,0.0-10.0,1312710,1048592
        20090314193213,172.16.201.131,5001,172.16.201.1,63132,3,0.0-10.0,1312710,1049881,0.838,0,893,0.000,0
        
        Output from plain mode or csv is pretty different (no jutter in csv)

        Doc test to verify that output is correct
        # >>> IperfOutput(["[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)"], "").result
        [[10.0, 1.0, 1.0, 6.0, 0, 893, 0]]
    """
    
    def __init__(self, conf = {}, value = 'kbs', format='PLAIN'):
        """Parser of iperf output, must manage every possible output,
        for example csv/not csv and double test mode
        Using the default Iperf configuration in none passed"""
        # first plain and second csv mode
        self.positions = {
            "bs"        : (4, 8),
            "jitter"    : (5, 9),
            "missed"    : (6, 10),
            "total"     : (7, 11)
        }
        # creating inverse lookups dictionaries for the two possible formats
        toIdx = lambda n: dict(zip([x[n] for x in self.positions.values()], self.positions.keys()))
        self.toPlainIdx = toIdx(0)
        self.toCsvIdx = toIdx(1)
        self.format = format
        # In this way I can set
        if self.format == 'PLAIN':
            self.dic = self.toPlainIdx
        elif self.format == 'CSV':
            self.dic = self.toCsvIdx

    def parseLine(self, line):
        """parse a single line"""
        result = {}
        if self.format == 'PLAIN':
            num = re.compile(r"(\d+)(?:\.(\d+))?")
            values = num.findall(line)
        if self.format == 'CSV':
            values = line[-1].strip().split(',')
        
        print "values found ", values
        # This way this works for both
        for el in self.dic.iterkeys():
            result[self.dic[el]] = toFlat(values[el])
        return result


class Opt:
    """General class for options, generates a ValueError exception whenever
    trying to set a value which is not feasible for the option"""
    def __init__(self, name, value = None):
        self.name = name
        self.value = value
    
    def iter_set(self, value):
        """Keep trying to set a value interactively until it's ok"""
        while True:
            try:
                self.set(value)
            except ValueError:
                print self.choices()
                self.iter_set(raw_input("continuing until it's ok\n"))
            else:
                break
    
    def __repr__(self):
        if not self.value:
            return ("parameter " + self.name, + " not set")
        else:
            return (self.name + " " + str(self.value))
    
    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.name == other.name and self.value == other.value

    def set(self, value):
        """Setting the value only if validity check is passed"""
        if self.valid(value):
            self.value = value
        else:
            raise ValueError, self.choices()
        

class BoolOpt(Opt):
    """Boolean option, if not set just give the null string"""
    def __init__(self, name, value = True):
        """By default the bool option is set (value True)"""
        Opt.__init__(self, name, value)

    def __repr__(self):
        if self.value:
            return self.name
        else:
            return ""

    # FIXME in interactive way it gets crazy with booleans
    def valid(self, value):
        return value in (True, False)
    
    def choices(self):
        return "must be True or False"

class ConstOpt(Opt):
    """Constant option, when you just have one possible value
    It optionally takes a regular expression used to check if input is syntactically correct"""
    def __init__(self, name, value = None, regex = None):
        self.regex = regex
        Opt.__init__(self, name, value)
    
    def valid(self, value):
        return not(self.regex) or re.match(self.regex, value)
    
    def choices(self):
        return "must satisfy " + self.regex
        
class ParamOpt(Opt):
    """Option with a parameter
    This takes a list of possible values and checks every time if input is safe"""
    def __init__(self, name, value = None, valList = []):
        self.valList = valList        
        Opt.__init__(self, name, value)

    def valid(self, value):
        return value in self.valList
    
    def choices(self):
        return "must be in list: " + ', '.join(map(str, self.valList))

class Plotter:
    """General plotter of data in array format
    maxGraphs indicates the maximum number of "functions" to be plotted
    at the same time"""
    def __init__(self, title, maxGraphs = 2):
        self.title = title
        self.items = []
        self.last = []
        self.maxGraphs = maxGraphs
        self.plotter = Gnuplot.Gnuplot(persist = 1)
    
    def addData(self, data, name):
        """Add another data set"""
        # always keeping last maxGraphs elements
        self.last = data
        new = Gnuplot.Data(data, with = "linespoints", title = name)
        self.items = self.items[ -self.maxGraphs : ] + [new]

    def plot(self):
        """docstring for plot"""
        self.plotter.plot(*self.items)
    
    def update(self, data):
        """Adds data to the last data set"""
        self.last += data
        new = Gnuplot.Data(self.last, with = "linespoints")
        if not self.items:
            self.items = [new]
        else:
            self.items[-1] = new
        self.plot()

    

class Conf:
    # remind that boolean options are set to true by default
    iperfConf = {
        "udp"   : BoolOpt("-u"),
        "band"  : ParamOpt("-b", 1, [1, 2, 5.5, 11]),
        "dual"  : BoolOpt("-d"),
        "host"  : ConstOpt("-c", "192.168.10.30"),
        "time"  : ParamOpt("-t", 20, [20,30,40]),
        "csv"   : BoolOpt("-y c")
    }
    def __init__(self, conf_file = "config.ini"):
        """"General configuration"""
        self.conf_file = conf_file
        self.configuration = {
            "iperf" : SectionConf("iperf", self.iperfConf)
        }
        self.reader = ConfigParser.ConfigParser()
        self.reader.readfp(open(conf_file))
    
    def __repr__(self):
        return "\n".join([x.__repr__() for x in self.configuration.values()]) 
        
    def defConf(self):
        for v in self.configuration.values():
            print v.def_conf
    
    def get_opt(self, section, name, opt):
        try:
            # FIXME not really nice programming style
            t = type(opt.value)
            if type(opt.value) == int:
                value = self.reader.getint(section, name)
            elif type(opt.value) == bool:
                value = self.reader.getboolean(section, name)
            else:
                value = self.reader.get(section, name)
                
        except Exception, e:
            print "no option for ", name
            
        else:
            try:
                opt.set(value)
            except ValueError, e:
                print "not valid value for %s in %s keeping default" % (name, section)
                
    def changed(self):
        changed = {}
        for key, val in self.configuration.iteritems():
            changed[key] = val.changed()
        return changed

    def update_conf(self):
        """Merge default configuration to configuration written to file"""
        for sec, conf in self.configuration.iteritems():
            for key, opt in conf.conf.iteritems():
                self.get_opt(sec, key, opt)
    
    def rand_config(self):
        """returns a random configuration"""
        from random import random, choice
        c = choice(self.conf)
        if isinstance(c, BoolOpt):
            c.swap()
        if isinstance(c, ParamOpt):
            c.rand_config()
    
    def configurator(self):
        """iterative configurator of iperf"""
        dic = dict(zip(range(len(self.conf)), self.conf))
        for k, v in dic.items():
            print "%d) %s" % (k, v)
        while True:
            num = input("make a choice")
            if num not in range(len(self.conf)):
                continue
            else:
                print "selected %d" % num


class SectionConf:
    """Configuration class, working on a dictionary of
    configurations parameters
    Using ConfigParser to write / read configuration parameters"""
    def __init__(self, name, def_conf):
        self.name = name
        # using deepcopy instead of =, otherwise it's just the same dictionary
        self.def_conf = def_conf
        self.conf = copy.deepcopy(self.def_conf)
    
    def __repr__(self):
        return ' '.join([el.__repr__() for el in self.conf.values()])
    
    def __str__(self):
        return self.__repr__()
        
    def changed(self):
        """Defining the minus operator on configurations"""
        changed = {}
        for key, val in self.def_conf.iteritems():
            print "checking ", self.conf[key], " equal to ", val
            if self.conf[key] != val:
                changed[key] = self.conf[key]
        return changed

class ApConf(object):
    """Configuration of an access point"""
    def __init__(self, arg):
        super(ApConf, self).__init__()

def makeOptions(opts):
    """Creating the option key for the dictionary, opts must be a dictionary of options"""
    return (sys.platform, opts, {})

# opts must contain {"client" : {...}, "ap" : {...}}
    

def toFlat(tup):
    """tuple to float
    # >>> toFlat((1,10))
    # 1.10
    """
    if tup[1] == '':
        return int(tup[0])
    return float(tup[0]) + (float(tup[1]) / 100)


# doing a simple split we get interesting results

if __name__ == '__main__':
    doctest.testmod()
