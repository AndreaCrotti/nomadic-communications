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

VERBOSE = False

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
    def __init__(self, name, value, val_list):
        self.val_list = val_list        
        Opt.__init__(self, name, value)

    def valid(self, value):
        return value in self.val_list
    
    def choices(self):
        return "must be in list: " + ', '.join(map(str, self.val_list))