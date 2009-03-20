#!/usr/bin/env python
import re
import doctest
import Gnuplot
import sys
import time
import shelve
import os

# right regular expression in shell (word boundary)
# grep '\<ms\>' result.txt

line = "[  3]  0.0-80.8 sec  1.25 MBytes    130 Kbits/sec  4.121 ms    0/  893 (0%)"
# num with comma
NUM = re.compile(r"(\d+)(?:\.(\d+))?")

class IperfOutput(object):
    """class to handle iperf outputs in different formats
        possible input formats are this (PLAIN):
        [  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)
        or the csv mode (CSV):
        20090314193213,172.16.201.1,63132,172.16.201.131,5001,3,0.0-10.0,1312710,1048592
        20090314193213,172.16.201.131,5001,172.16.201.1,63132,3,0.0-10.0,1312710,1049881,0.838,0,893,0.000,0
        
        Output from plain mode or csv is pretty different (no jutter in csv)

        Doc test to verify that output is correct
        >>> IperfOutput(["[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)"], "").result
        [[10.0, 1.0, 1.0, 6.0, 0, 893, 0]]
    """

    
    def __init__(self, text, conf, value = 'kbs', format='PLAIN'):
        """text is an open file in read mode"""
        self.idxToName = {
            2 : "time",
            3 : "mb",
            4 : "kbs",
            5 : "ms",
            6 : "miss",
            7 : "rx",
            8 : "cent"
        }
        # creating the inverse dictionary
        self.nameToIdx = dict(zip(self.idxToName.values(), self.idxToName.keys()))        
        self.text = text
        self.format = format
        self.conf = conf
        self.result = []
    
    def nextResult(self):
        for line in self.text.xreadlines():
            if self.format == 'PLAIN':
                # only if really a result line
                if re.search(r"\bms\b", line):
                    parsed = self.parsePlain(line)
                    self.result.append(parsed)
                    yield(parsed[self.nameToIdx['mb']])
            elif format == 'CSV':
                parsed = self.parseCsv(line)
                self.result.append(parsed[self.nameToIdx['mb']])
                yield(parsed[2])
            else:
                print "format not available"
        
    def parsePlain(self, line):
        """parsing the plain structure"""
        num = re.compile(r"(\d+)(?:\.(\d+))?")
        values = num.findall(line)
        valList = []
        for c in self.idxToName.iterkeys():
            valList.append(toFlat(values[c]))
        return valList
        
    def parseCsv(self, line):
        """Same thing but much easier"""
        return self.text.split(',')

class Opt:
    """General class for options"""
    def __init__(self, name, value):
        self.name = name
        self.iter_set(value)
    
    def iter_set(self, value):
        while True:
            try:
                self.set(value)
            except ValueError:
                print self.choices()
                self.iter_set(raw_input("continuing until it's ok\n"))
            else:
                break
    
    def __repr__(self):
        return (self.name + " " + str(self.value))
    
    def valid(self):
        return True
        
    def set(self, value):
        if self.valid(value):
            self.value = value
        else:
            raise ValueError, self.choices()
        

class BoolOpt(Opt):
    """Boolean option, if not set just give the null string"""
    def __init__(self, name):
        Opt.__init__(self, name, True)

    def swap(self):
        """swap status"""
        self.value = not self.value
    
    def on(self):
        """turn on variable"""
        self.value = True
    
    def off(self):
        """turn off variable"""
        self.value = False
    
    # FIXME in interactive way it gets crazy with booleans
    def valid(self, value):
        return value in (True, False)
    
    def choices(self):
        return "must be True or False"

class ConstOpt(Opt):
    """Constant option, when you just have one possible value"""
    def __init__(self, name, value, regex = None):
        self.regex = regex
        Opt.__init__(self, name, value)
    
    def valid(self, value):
        return not(self.regex) or re.match(self.regex, value)
    
    def choices(self):
        return "must satisfy " + regex
            
        
class ParamOpt(Opt):
    """Option with a parameter
    This takes a list of possible values and checks every time if input is safe"""
    def __init__(self, name, value, valList):
        self.valList = valList        
        Opt.__init__(self, name, value)

    def valid(self, value):
        return value in self.valList
    
    def choices(self):
        return "must be in list: " + ', '.join(map(str, self.valList))

    def rand_config(self):
        """gets a random choice"""
        from random import choice
        self.value = choice(self.valList)

    def next_config(self):
        """get the next possible configuration"""
        self.value = self.valList[(self.valList.index(self.value) + 1) % len(self.valList)]

class Size:
    """docstring for Size"""
    def __init__(self, num, idx):
        self.num = num
        self.idx = idx
    
    def toM(self):
        """to megabytes"""
        pass
    

class Plotter:
    """General plotter of data in array format
    maxGraphs indicates the maximum number of "functions" to be plotted
    at the same time"""
    def __init__(self, title, maxGraphs = 2):
        self.title = title
        self.items = []
        self.last = []
        self.maxGraphs = maxGraphs
        self.plotter = Gnuplot.Gnuplot()
    
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

def testPlotter():
    """docstring for testPlotter"""
    import random
    p = Plotter("test")
    # using * to autoscale one of the variables
    p.plotter.set_range('yrange', '[0:*]')
    p.addData([50 + random.randrange(5)], "random")
    for x in range(100):
        p.update([50 + random.randrange(5)])
        time.sleep(0.05)
    p.addData([30 + random.randrange(20)], "random2")
    for x in range(100):
        p.update([30 + random.randrange(20)])
        time.sleep(0.05)
        
    p.addData([20 + random.randrange(5)], "random3")
    for x in range(100):
        p.update([20 + random.randrange(5)])
        time.sleep(0.05)
        
def iperfAnalyzer():
    """Generates the configuration, executes the program and plot it"""
    iperf = Plotter("iperf output")
    for count in range(10):
        i = IperfConf("lts")
        cmd = "iperf " + str(IperfConf("lts"))
        # print cmd
        _, w, _ = os.popen3(cmd)
        out = IperfOutput(w, {})
        for x in out.nextResult():
            print x, "\t",  out.result
            iperf.update([x])
    

class Conf:
    """Configuration class, working on a dictionary of
    configurations parameters"""
    def __init__(self, conf):
        # Check if hostname is actually reachable?
        self.conf = conf
        
    def __repr__(self):
        return " ".join([str(opt) for opt in self.conf])
    
    def __str__(self):
        return self.__repr__()
    
    def update_conf(self, opt, value):
        pass
    
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
                
    def set(self, option, value):
        """ValueError raised if out of range"""
        self.conf[option].set(value)
        

            
class IperfConf(Conf):
    """Iperf configurator"""
    def __init__(self, hostname):
        self.hostname = hostname
        udp = BoolOpt("-u")
        band = ParamOpt("-b", 1, [1,2,10])
        dual = BoolOpt("-d")
        host = ParamOpt("-c", self.hostname, [self.hostname])
        time = ParamOpt("-t", 10, [10, 20, 30])
        conf = [udp, band, dual, host]
        Conf.__init__(self, conf)


speed = [1, 2, 5.5, 11]

linksys = {
    "ssid" : "NCB",
    "ip" : "192.168.10.5"
}

cisco1 = {
    "ssid" : "NCG",
    "ip" : "192.168.10.10"
}

cisco2 = {
    "ssid" : "NCL",
    "ip" : "192.168.10.15"
}


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
    return round(float(tup[0]) + (float(tup[1]) / 100))


# doing a simple split we get interesting results

if __name__ == '__main__':
    doctest.testmod()
