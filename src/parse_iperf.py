#!/usr/bin/env python
# encoding: utf-8

import re
import sys
import logging
from utils import Size, tuple_to_num

class IperfClient(object):
    """Handling parsing of iperf, getting one line at a time or a file"""
    
    def __init__(self, format):
        # inverting the dictionary
        self.format = format
        self.fields = ["avg", "missed", "total", "jitter", "transfer"]
        self.result = dict(zip(self.fields, [None] * len(self.fields)))
        self.result['values'] = []
    
    def __str__(self):
        return str(self.result)
    
    def __repr__(self):
        return str(self)

    def parse_file(self, filename):
        "Parsing a file, taking as an open 'r' file"
        for line in filename:
            self.parse_line(line)
    
    def get_values(self):
        return self.result['values']

class IperfClientCsv(IperfClient):
    """Handling iperf output in csv mode"""
    def __init__(self):
        self.positions = {
            "transfer" : 7, "avg" : 8, "jitter" : 9, "missed" : 10, "total" : 11
        }
        IperfClient.__init__(self, format = 'CSV')
        self.splitted = lambda line: line.strip().split(',')
    
    def _translate(self, val):
        v = int(val)
        return str(Size(v, 'B').translate('K'))

    def parse_line(self, line):
        l = self.splitted(line)
        if len(l) == 9:
            self.result['values'].append(self._translate(l[-1]))
        elif len(l) == 14:
            for p in self.positions.keys():
                self.result[p] = l[self.positions[p]]
            self.result["transfer"] = self._translate(self.result["transfer"])
        # otherwise automatically do nothing, empty line probably

class IperfClientPlain(IperfClient):
    """Handling iperf not in csv mode"""
    def __init__(self):
        self.positions = {
            "transfer" : 3, "avg" : 4, "jitter" : 5, "missed" : 6, "total" : 7
        }
        self.num = re.compile(r"(\d+)(?:\.(\d+))?")
        IperfClient.__init__(self, format = 'PLAIN')
 
    def parse_line(self, line):
        if re.search(r"\bKBytes\b", line):
            nums = self.num.findall(line)
            values = map(tuple_to_num, nums)
            if re.search(r"\bms\b", line):
                for p in self.positions.keys():
                    self.result[p] = values[self.positions[p]]
            else:
                self.result['values'].append(values[-1])

class IperfServer(object):
    def __init__(self):
        self.positions = {
            "speed" : 4, "jitter" : 5, "missed" : 6, "total" : 7
        }
        self.num = re.compile(r"(\d+)(?:\.(\d+))?")
        self.results = {}
    
    def parse_file(self, filename):
        # last line not evaluated
        for line in filename.readlines()[:-1]:
            self.parse_line(line)
    
    def parse_line(self, line):
        if re.search(r"\bKBytes\b", line):
            nums = self.num.findall(line)
            values = map(tuple_to_num, nums)
            logging.debug("values found %s" % str(values))
            for s in self.positions.keys():
                val = values[self.positions[s]]
                if self.results.has_key(s):
                    self.results[s].append(val)
                else:
                    self.results[s] = [val]

    def get_values(self, field = 'speed'):
        # leaving exception handling outside
        return self.results[field]