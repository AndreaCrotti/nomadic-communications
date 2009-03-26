#!/usr/bin/env python
# encoding: utf-8

# =================================================================
# = This python program allows to automatize the creation         =
# = and analysis of test using iperf to test network performances =
# =================================================================

import re
import sys
import shelve
import os
import ConfigParser
import copy
import time
import code
import getopt

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

VERBOSE = True

speeds = ['1M', '2M', '5.5M', '10M']
frag = []

def interactive():
    def frag():
        for f in frag:
            pass
    def speedy():
        for s in speeds:
            print "set speed %s on your access point" % s
            while True:
                ans = raw_input("press Y when done")
                if ans == "Y": break
                else: continue
        
            test.conf['iperf']['band'].set(s)
            test.conf['ap']['speed'].set(s)
            test.run_tests()
    print "starting tests, edit config.ini with the informations about your access point"
    # magic number
    test = TestConf(4)
    host = raw_input("which host is your server")
    test.conf['iperf']['host'].set(host)
    speedy()
    
# ==========================
# = Configuration analysis =
# ==========================
class TestConf:
    def __init__(self, num_tests, conf = None):
        """docstring for __init__"""
        self.num_tests = num_tests
        if not(conf):
            self.conf = Conf()
        else: self.conf = conf
        
        # udp = self.conf['iperf']['udp'].value
        # leaving default with csv
        self.analyzer = IperfOutPlain(udp = True)
        self.conf['iperf']['csv'].unset()
        date = time.strftime("%d-%m-%Y", time.localtime())
        self.get_time = lambda: time.strftime("%H:%M", time.localtime())
        self.output = shelve.open("test_result-" + date)
        # The None values are filled before written to shelve dictionary
        self.test_conf = {
            "platform"  : os.uname(),
            "conf"      : self.conf,
            "start"     : None,
            "end"       : None,
            "result"    : None
        }
    
    def __repr__(self):
        return repr(self.test_conf)

    def run_tests(self):
        """Runs the test num_tests time and save the results"""
        cmd = str(self.conf['iperf'])
        print "your actual configuration is %s" % self.test_conf
        self.test_conf["start"] = self.get_time()
        print "executing %s" % cmd
        for counter in range(self.num_tests):
            print "%d))\t" % counter,
            _, w, e = os.popen3(cmd)
            for line in w.readlines():
                val = self.analyzer.parse_line(line)
                # only when "good lines"
                if val:
                    print "%s\n" % val[self.analyzer.value]
                
        self.test_conf["end"] = self.get_time()
        self.test_conf["result"] = self.analyzer.get_values()
        # =========================================================================
        # = IMPORTANT, if given twice the same conf it overwrites the old results =
        # =========================================================================
        self.output[str(self.conf)] = self.test_conf
        self.output.sync()
        self.output.close()
        # self.output[repr(self.test_conf)] = self.analyzer.get_values()
        # Only plotting if gnuplot available
        if GNUPLOT:
            self.plotter = Plotter("testing", "kbs")
            self.plotter.add_data(self.test_conf["result"], "testing")
            self.plotter.plot()


class Size:
    """ Converting from one unit misure to the other """
    def __init__(self, value, unit = 'B'):
        self.value = value
        self.units = ['B', 'K', 'M', 'G']
        if unit not in self.units:
            raise ValueError, "unit must be in " + str(self.units)
        self.unit = unit

    def translate(self, unit):
        """Returns the rounded translation in a different unit measure"""
        if unit not in self.units:
            raise ValueError, "can only choose " + self.units
        else:
            offset = self.units.index(self.unit) - self.units.index(unit)
            return round(self.value * (pow(1024, offset)), 2)

    def findUnit(self):
        """Finds the best unit misure for a number"""
        val = self.value
        un = self.unit
        while val > 1024 and self.units.index(un) < len(self.units):
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
        
    # TODO implementing the efficiency of the channel
    
    
# ==========================================
# = Handling iperf output in various forms =
# ==========================================
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
    
    def __init__(self, format, udp = True, value = 'kbs'):
        # inverting the dictionary
        self.udp = udp
        self.fromIdx = dict(zip(self.positions.values(), self.positions.keys()))
        self.value = value
        self.format = format
        self.result = []

    # TODO creating an iterator
    def parse_line(self, line):
        """parse a single line
        FIXME Creating a dictionary for every line isn't very efficient"""
        result = {}
        # TCP case
        if not(self.udp):
            kbs = self.parse_tcp(line)
            result[self.value] = kbs
        # UDP case
        else:
            values = self.parse_udp(line)
        # doing nothing if useless line
            if not(values):
                return
            for el in self.fromIdx.iterkeys():
                result[self.fromIdx[el]] = values[el]
        self.result.append(result)
        return result # FIXME create an iterator with next, __iter__
    
    def parse_file(self, filename):
        "Takes the filename"
        for line in open(filename):
            self.parse_line(line)
    
    def get_values(self):
        return [el[self.value] for el in self.result]


class IperfOutCsv(IperfOutput):
    """Handling iperf output in csv mode"""
    def __init__(self, udp = True):
        self.positions = {
            "kbs" : 8, "jitter" : 9, "missed" : 10, "total" : 11
        }
        IperfOutput.__init__(self, udp = udp, format = 'CSV')
        self.splitted = lambda line: line.strip().split(',')
    
    def _translate(self, val):
        v = int(val)
        return str(Size(v, 'B').translate('K'))

    def parse_tcp(self, line):
        """Returning just the bandwidth value in KB/s"""
        return self._translate(self.splitted(line)[-1])

    def parse_udp(self, line):
        fields = self.splitted(line)
        # FIXME a bit ugly way to translate last value to kbs
        kbsidx = self.positions[self.value]
        fields[kbsidx] = self._translate(fields[kbsidx])
        return fields
        
class IperfOutPlain(IperfOutput):
    """Handling iperf not in csv mode"""
    def __init__(self, udp = True):
        self.positions = {
            "kbs" : 4, "jitter" : 5, "missed" : 6, "total" : 7
        }
        self.num = re.compile(r"(\d+)(?:\.(\d+))?")
        IperfOutput.__init__(self, udp = udp, format = 'PLAIN')

    def parse_tcp(self, line):
        """if using tcp mode changes everything, line becomes for example 
        [  3]  0.0- 5.0 sec  3312 KBytes    660 KBytes/sec
        Only gives back the bandwidth"""
        return self.__fun(self.num.findall(line)[-1])
    
    def parse_udp(self, line):
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
        
# ================================
# = Classes for handling options =
# ================================
class Opt:
    """General class for options, generates a ValueError exception whenever
    trying to set a value which is not feasible for the option"""
    def __init__(self, name, value = None):
        self.name = name
        self.value = value
        self.setted = True
    
    def __repr__(self):
        if not self.setted:
            return ''
        else:
            return (self.name + " " + str(self.value))
    
    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        """checking equality of option types, also type must be equal"""
        return type(self) == type(other) and self.name == other.name and self.value == other.value

    # def valid(self):
    #     assert 0, 'valid must be implemented'
    # 
    # def choices(self):
    #     assert 0, 'choices must be implemented'

    def unset(self):
        """Unset the option, to disable representation"""
        self.setted = False

    def set(self, value):
        """Setting the value only if validity check is passed"""
        self.setted = True
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
        if not self.setted:
            return ''
        else:
            return self.name
    
    
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

class Conf:
    # remind that boolean options are set to true by default
    iperfConf = {
        "host"  : ConstOpt("-c", "192.168.10.30"),
        "udp"   : BoolOpt("-u"),
        "band"  : ParamOpt("-b", '1M', ['1M', '2M', '5.5M', '11M']),
        # "dual"  : BoolOpt("-d", False),
        "time"  : ParamOpt("-t", 5, [5, 20, 30, 40]),
        "csv"   : BoolOpt("-y c", False),
        "format": ConstOpt("-f", "K")      # defaulting to kiloBytes
    }
    apConf = {
        "speed"             : ParamOpt("speed", '11M', ['1M', '2M', '5.5M', '11M']),
        # "mode"              : ParamOpt("mode", "g", ["g", "b"]),
        "frag_threshold"    : ParamOpt("frag_threshold", 1500, range(256,1501)),
        "rts_threshold"     : ParamOpt("rts_threshold", 2436, range(256, 2437)),
        "ssid"              : ConstOpt("ssid", "NCB"),
        "ip"                : ConstOpt("ip", "192.168.10.10")
    }
    nicConf = {
        "speed"             : ParamOpt("speed", 11, [1, 2, 5.5, 11])
    }
    # TODO see if config file is necessary or not
    def __init__(self): # , conf_file = "config.ini"):
        """"General configuration"""
        self.configuration = {
            # dirty trick to allow keeping the right order during visualization (creation of command)
            "iperf" : SectionConf("iperf", self.iperfConf, order = ["host", "udp", "band", "time", "csv", "format"]),
            "ap"    : SectionConf("ap", self.apConf),
            "nic"   : SectionConf("nic", self.nicConf)
        }
        self.writer = ConfigParser.ConfigParser()
        
    
    def __repr__(self):
        return "\n".join([(key + ":\t" + repr(val)) for key, val in self.configuration.items()])
        
    def __str__(self):
        return self.__repr__()

    def __getitem__(self, idx):
        return self.configuration[idx]
        
    def def_conf(self):
        for v in self.configuration.values():
            print v.def_conf
    
    def get_option(self, section, name, opt):
        try:
            # FIXME not really nice programming style
            t = type(opt.value)
            if t == int:
                value = self.reader.getint(section, name)
            elif t == bool:
                value = self.reader.getboolean(section, name)
            else:
                value = self.reader.get(section, name)
                
        except Exception:
            print "no option for ", name
            
        else:
            try:
                opt.set(value)
            except ValueError, e:
                print "not valid value for %s in %s keeping default" % (name, section)
                
    def show_conf(self):
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

    def update_conf(self):
        """Merge default configuration with configuration written to file"""
        for sec, conf in self.configuration.iteritems():
            for key, opt in conf.conf.iteritems():
                self.get_option(sec, key, opt)

class SectionConf:
    """Configuration class, working on a dictionary of
    configurations parameters
    Using ConfigParser to write / read configuration parameters
    order changes only the visualization order if not null"""
    def __init__(self, name, def_conf, order = []):
        self.order = order
        self.name = name
        # using deepcopy instead of =, otherwise it's just the same dictionary
        self.def_conf = def_conf
        self.conf = copy.deepcopy(self.def_conf)
    
    def __repr__(self):
        opts = []
        if self.order:
            if len(self.order) != len(self.conf.keys()):
                raise Exception, "order must be complete if given"
            else:
                opts = [repr(self.conf[key]) for key in self.order]
        else:
            opts = [repr(el) for el in self.conf.values()]
        return ' '.join([self.name] + opts)
    
    def __str__(self):
        return repr(self)
    
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
    
    def write_options(self):
        """Writes out options"""
        for el, val in self.def_conf.items():
            print el, val.choices()
        
if __name__ == '__main__':
    test = TestConf(10, "koalawlan")
    test.run_test()