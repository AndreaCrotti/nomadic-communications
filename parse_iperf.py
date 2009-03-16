#!/usr/bin/env python
import re
import doctest
import Gnuplot
import sys
import time

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
    def __init__(self, text, conf, format='PLAIN'):
        super(IperfOutput, self).__init__()
        self.text = text
        self.format = format
        self.conf = conf
        self.result = []

        for line in text:
            if format == 'PLAIN':
                # only if really a result line
                if re.search(r"\bms\b", line):
                    self.result.append(self.parsePlain(line))
            elif format == 'CSV':
                self.result.append(self.parseCsv(line))
            else:
                print "format not available"
        
    def parsePlain(self, line):
        """parsing the plain structure"""
        num = re.compile(r"(\d+)(?:\.(\d+))?")
        cells = {
            2 : "time",
            3 : "mb",
            4 : "kbs",
            5 : "ms",
            6 : "miss",
            7 : "rx",
            8 : "cent"
        }
        values = num.findall(line)
        valList = []
        for c in cells.iterkeys():
            valList.append(toFlat(values[c]))
        return valList
        
    def parseCsv(self, line):
        """Same thing but much easier"""
        return self.text.split(',')
        
class BoolOpt:
    """boolean option, init takes a dictionary when option is true or false"""
    def __init__(self, name, optValues, default = True):
        self.name = name
        self.optValues = optValues
        self.default = default
        self.reset()
        
    def reset(self):
        """docstring for reset"""
        self.value = self.default
        
    def __repr__(self):
        """docstring for __repr__"""
        return self.optValues[self.value]
    
class ParamOpt:
    """Option with a parameter"""
    def __init__(self, name, flag, defValue, values):
        self.flag = flag
        self.name = name
        self.defValue = defValue
        self.values = values
        self.reset()
        
    def reset(self):
        """docstring for reset"""
        self.actual = self.defValue

    def __repr__(self):
        """docstring for __repr__"""
        return " ".join([self.flag, str(self.actual)])
    
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
    """Plotting results coming from iperf"""
    def __init__(self, title, data = []):
        self.title = title
        self.data = data
        self.plotter = Gnuplot.Gnuplot(persist = 1)
        
    def setPlot(self, data):
        """setting plotId"""
        self.plotId = Gnuplot.PlotItems.Data(data, with = "lines", title = self.title)
    
    def addData(self, data):
        self.data += data
        self.setPlot(self.data)

    def replot(self, *data):
        """docstring for plot"""
        self.addData(data)
        self.plotter.plot(self.plotId)
        
    def addFunction(self):
        """docstring for addFunction"""
        pass
        

class IperfConf(object):
    """configuration for iperf"""
    def __init__(self, hostname, conf = None):
        # Check if hostname is actually reachable?
        self.hostname = hostname
        if conf:
            self.conf = conf
        else:
            defConf = {
                "proto" : "-u",
                "band"  : 1,
                "dual"  : False,
                "time"  : 10
            }
            conf = {
                "proto" : ["-u", ""], # running udp by default
                "band"  : {"-b" : [1, 2, 10]},
                "dual"  : ["", "-d"], # not bidirectional by default
                "time"  : {"-t" : [10, 20, 30]}
            }
            

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
