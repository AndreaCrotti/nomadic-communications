#!/usr/bin/env python
import re
import sys
import shelve
import os
import ConfigParser
import copy

GNUPLOT = True
try:
    import Gnuplot
except ImportError, i:
    print "you will be unable to plot in real time"
    GNUPLOT = False

STAT = True
try:
    from statlib import stats
except ImportError, i:
    print "not able to do the statistical analysis"
    STAT = False

class Size:
    """Size units:
    b/B, kb/Kb, mb/Mb, gb/Gb"""
    def __init__(self, value, unit):
        self.value = value
        self.unit = unit
        self.units = ['b', 'kb', 'mb', 'gb']
    
    def findUnit(self):
        val = self.value
        un = self.unit
        while val > 1024:
            val /= float(1024)
            # going to the next
            un = self.units[self.units.index(un) + 1]
        return Size(val, un)
        
    def __repr__(self):
        return " ".join([str(self.value), self.unit])
    
class StatData:
    """Statistical computations on data"""
    def __init__(self, data):
        self.data = data
        self.mean = stats.mean(data)
        self.stdev = stats.stdev(data)
    
    def __repr__(self):
        return "\n".join(["values:\t" + repr(self.data), "mean:\t" + repr(self.mean), "stdev:\t" + repr(self.stdev)])
    
    
class IperfOutput(object):
    """class to handle iperf outputs in different formats
        possible input formats are this (PLAIN):
        [  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)
        or the csv mode (CSV):
        20090314193213,172.16.201.1,63132,172.16.201.131,5001,3,0.0-10.0,1312710,1048592
        20090314193213,172.16.201.131,5001,172.16.201.1,63132,3,0.0-10.0,1312710,1049881,0.838,0,893,0.000,0
        
        The bigger problem is about measures, csv doesn't take the -f option and plain doesn't output in bytes/sec

        The philosophy behind this output analyzer is:
        "keep everything return only what's needed"
    """
    
    def __init__(self, format = 'CSV', value = 'bs'):
        # inverting the dictionary
        self.fromIdx = dict(zip(self.positions.values(), self.positions.keys()))
        self.value = value
        self.format = format
        self.result = []

    def parseLine(self, line):
        """parse a single line
        FIXME Creating a dictionary for every line isn't very efficient"""
        result = {}
        # calling the function defined in subclasses
        values = self.parseValues(line)
        print "obtained ", values
        # doing nothing if useless line
        if not(values):
            return
        for el in self.fromIdx.iterkeys():
            result[self.fromIdx[el]] = values[el]
        print result
        self.result.append(result)
    
    def parseFile(self, filename):
        "Takes the filename"
        for line in open(filename):
            self.parseLine(line)
    
    def getValues(self):
        return [el[self.value] for el in self.result]

class IperfOutCsv(IperfOutput):
    """Handling iperf output in csv mode"""
    def __init__(self):
        self.positions = {
            "bs" : 8, "jitter" : 9, "missed" : 10, "total" : 11
        }
        IperfOutput.__init__(self, format = 'CSV')
        

    def parseValues(self, line):
        splitted = line.strip().split(',')
        if len(splitted) >= 11:
            return splitted
        else: 
            return None
        
        
class IperfOutPlain(IperfOutput):
    """Handling iperf not in csv mode"""
    def __init__(self):
        self.positions = {
            "bs" : 4, "jitter" : 5, "missed" : 6, "total" : 7
        }
        IperfOutput.__init__(self, format = 'PLAIN')

    def parseValues(self, line):
        if re.search(r"\bms\b", line):
            num = re.compile(r"(\d+)(?:\.(\d+))?")
            nums = num.findall(line)
            values = map(self.__fun, nums)
            return values
        else:
            return None
    
    def __fun(self, tup):
        """Taking float numbers in a list of tuples"""
        return float('.'.join([tup[0], tup[1]]))
        

class Opt:
    """General class for options, generates a ValueError exception whenever
    trying to set a value which is not feasible for the option"""
    def __init__(self, name, value = None):
        self.name = name
        self.value = value
    
    def iterSet(self, value):
        """Keep trying to set a value interactively until it's ok"""
        while True:
            try:
                self.set(value)
            except ValueError:
                print self.choices()
                self.iterSet(raw_input("continuing until it's ok\n"))
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
        """checking equality of option types, also type must be equal"""
        return type(self) == type(other) and self.name == other.name and self.value == other.value

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

    def valid(self, value):
        return value in (True, False)
    
    def choices(self):
        return "True, False"

class ConstOpt(Opt):
    """Constant option, when you just have one possible value
    It optionally takes a regular expression used to check if input is syntactically correct"""
    def __init__(self, name, value = None, regex = None):
        self.regex = regex
        Opt.__init__(self, name, value)
    
    def valid(self, value):
        return (not(self.regex) or re.match(self.regex, value))
    
    # FIXME strange TypeError: cannot concatenate 'str' and 'NoneType' objects error
    def choices(self):
        if not(self.regex):
            return "whatever"
        else:
            return ("must satisfy regex: " + self.regex)
        
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
    
    def addData(self, data, name):
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
    
def testMany():
    p = Plotter("titolo", "bs")
    p.addData(range(10), "range")
    p.addData([4]*10, "const")
    p.addData([stats.mean(range(10))] * 10, "avg")
    p.plot()

class Conf:
    # remind that boolean options are set to true by default
    iperfConf = {
        "udp"   : BoolOpt("-u"),
        "band"  : ParamOpt("-b", 1, [1, 2, 5.5, 11]),
        "dual"  : BoolOpt("-d", False),
        "host"  : ConstOpt("-c", "192.168.10.30"),
        "time"  : ParamOpt("-t", 20, [5, 20,30,40]),
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
        self.writer = ConfigParser.ConfigParser()
        
    
    def __repr__(self):
        return "\n".join([(key + " " + val.__repr__()) for key, val in self.configuration.items()])
        
    def __str__(self):
        return self.__repr__()

    def __getitem__(self, idx):
        return self.configuration[idx]
        
    def defConf(self):
        for v in self.configuration.values():
            print v.def_conf
    
    def getOpt(self, section, name, opt):
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
                
    def showConf(self):
        for sec, val in self.configuration.items():
            self.writer.add_section(sec)
            for key, v in val.conf.items():
                self.writer.set(sec, key, v.value)
        self.writer.write(sys.stdout)

    def changed(self):
        changed = {}
        for key, val in self.configuration.iteritems():
            changed[key] = val.changed()
        return changed

    def updateConf(self):
        """Merge default configuration with configuration written to file"""
        for sec, conf in self.configuration.iteritems():
            for key, opt in conf.conf.iteritems():
                self.getOpt(sec, key, opt)

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
        return ' '.join([self.name] + [el.__repr__() for el in self.conf.values()])
    
    def __str__(self):
        return self.__repr__()
    
    def __getitem__(self, idx):
        return self.conf[idx]

    # FIXME not working, doesn't get the right thing
    def changed(self):
        """Defining the minus operator on configurations"""
        changed = {}
        for key, val in self.def_conf.iteritems():
            if self.conf[key] != val:
                changed[key] = self.conf[key]
        return SectionConf("diff", changed)
    
    def writeOptions(self):
        """Writes out options"""
        for el, val in self.def_conf.items():
            print el, val
            print el, val.choices()
        
