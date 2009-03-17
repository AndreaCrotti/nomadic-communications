#!/usr/bin/env python
import re
import doctest
import Gnuplot
import sys
import time
import shelve

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

        Doc test to verify that output is correct
        >>> IperfOutput(["[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)"], "").result
        [[10.0, 1.0, 1.0, 6.0, 0, 893, 0]]
    """
    cells = {
        2 : "time",
        3 : "mb",
        4 : "kbs",
        5 : "ms",
        6 : "miss",
        7 : "rx",
        8 : "cent"
    }
    def __init__(self, text, conf, value = 'kbs', format='PLAIN'):
        super(IperfOutput, self).__init__()
        self.text = text
        self.format = format
        self.conf = conf
        self.result = []
    
    def nextResult(self):
        for line in self.text:
            if self.format == 'PLAIN':
                # only if really a result line
                if re.search(r"\bms\b", line):
                    parsed = self.parsePlain(line)
                    self.result.append(parsed)
                    yield(parsed[3])
            elif format == 'CSV':
                parsed = self.parseCsv(line)
                self.result.append(parsed)
                yield(parsed[3])
            else:
                print "format not available"
        
    def parsePlain(self, line):
        """parsing the plain structure"""
        num = re.compile(r"(\d+)(?:\.(\d+))?")
        values = num.findall(line)
        valList = []
        for c in IperfOutput.cells.iterkeys():
            valList.append(toFlat(values[c]))
        return valList
        
    def parseCsv(self, line):
        """Same thing but much easier"""
        return self.text.split(',')
        
class BoolOpt:
    """Boolean option, if not set just give the null string"""
    def __init__(self, name, flag):
        self.name = name
        self.flag = flag
        self.set = True

    def __repr__(self):
        """docstring for __repr__"""
        if self.set:
            return self.flag
        else:
            return ""            
 
    def __str__(self):
        """docstring for __repr__"""
        return self.__repr__()
    
    def swap(self):
        """swap status"""
        self.set = not self.set
    
    def on(self):
        """turn on variable"""
        self.set = True
    
    def off(self):
        """turn off variable"""
        self.set = False
    
        
class ParamOpt:
    """Option with a parameter"""
    def __init__(self, name, flag, defValue, values):
        if not values:
            values = [defValue]
        if defValue not in values:
            print "default value not in values"
            self.defValue = values[0]
        else:
            self.defValue = defValue
        self.flag = flag
        self.name = name
        self.values = values
        self.reset()

    def reset(self):
        """docstring for reset"""
        self.actual = self.defValue

    def __repr__(self):
        """docstring for __repr__"""
        return " ".join([self.flag, str(self.actual)])
        
    def __str__(self):
        """docstring for __str__"""
        return self.__repr__()
    
    def rand_config(self):
        """gets a random choice"""
        from random import choice
        self.actual = choice(self.values)

    def next_config(self):
        """get the next possible configuration"""
        self.actual = self.values[(self.values.index(self.actual) + 1) % len(self.values)]

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
        self.maxGraphs = maxGraphs
        self.plotter = Gnuplot.Gnuplot(persist = 1)
        
    def addData(self, data, name):
        """Add another data set"""
        # always keeping last maxGraphs elements
        self.last = data
        self.items = self.items[ -self.maxGraphs : ] + [Gnuplot.Data(data, with = "lines", title = name)]

    def plot(self):
        """docstring for plot"""
        self.plotter.plot(*self.items)
    
    def update(self, data):
        """Adds data to the last data set"""
        self.last += data
        self.items[-1] = Gnuplot.Data(self.last, with = "lines")
        self.plot()

def testPlotter():
    """docstring for testPlotter"""
    import random
    import time
    p = Plotter("test")
    p.addData([50 + random.randrange(5)], "random")
    for x in range(100000):
        p.update([50 + random.randrange(5)])
        time.sleep(0.05)
        
def iperfAnalyzer():
    """Generates the configuration, executes the program and plot it"""
    iperf = Plotter("iperf output")
    i = IperfConf("koala")    
    

class Conf:
    """Configuration class"""
    def __init__(self, conf):
        # Check if hostname is actually reachable?
        self.conf = conf
        
    def __repr__(self):
        return " ".join([str(opt) for opt in self.conf])
    
    def __str__(self):
        return self.__repr__()
    
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
                
            
class IperfConf(Conf):
    """Iperf configurator"""
    def __init__(self, hostname):
        self.hostname = hostname
        udp = BoolOpt("udp", "-u")
        band = ParamOpt("band", "-b", 1, [1,2,10])
        dual = BoolOpt("dual", "-d")
        host = ParamOpt("host", "-c", self.hostname, [self.hostname])
        time = ParamOpt("time", "-t", 10, [10, 20, 30])
        conf = [udp, band, dual, host]
        Conf.__init__(self, conf)


class ApConf(object):
    """Configuration of an access point"""
    def __init__(self, arg):
        super(ApConf, self).__init__()

def makeOptions(opts):
    """Creating the option key for the dictionary, opts must be a dictionary of options"""
    return (sys.platform, opts, {})

# opts must contain {"client" : {...}, "ap" : {...}}

def launchTest(opts):
    """Launch n times a test and put the result in a dictionary"""
    dic = makeOptions(opts)
    format = "%d/%m/%Y - %H:%M"
    dic[2]["start"] = time.strftime(format)
    read, write = os.popen2("iperf -c " + HOST + opts)
    dic[2]["end"] = time.strftime(format)
    

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
