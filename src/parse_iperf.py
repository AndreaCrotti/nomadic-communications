#!/usr/bin/env python
# encoding: utf-8

import re
from utils import Size

# ==========================================
# = Handling iperf output in various forms =
# ==========================================
class IperfOutput(object):
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

class IperfOutCsv(IperfOutput):
    """Handling iperf output in csv mode"""
    def __init__(self):
        self.positions = {
            "transfer" : 7, "avg" : 8, "jitter" : 9, "missed" : 10, "total" : 11
        }
        IperfOutput.__init__(self, format = 'CSV')
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
        
class IperfOutPlain(IperfOutput):
    """Handling iperf not in csv mode"""
    def __init__(self):
        self.positions = {
            "transfer" : 3, "avg" : 4, "jitter" : 5, "missed" : 6, "total" : 7
        }
        self.num = re.compile(r"(\d+)(?:\.(\d+))?")
        IperfOutput.__init__(self, format = 'PLAIN')
 
    def parse_line(self, line):
        if re.search(r"\bKBytes\b", line):
            nums = self.num.findall(line)
            values = map(self._fun, nums)
            if re.search(r"\bms\b", line):
                for p in self.positions.keys():
                    self.result[p] = values[self.positions[p]]
            else:
                self.result['values'].append(values[-1])
    
    def _fun(self, tup):
        """Taking float numbers in a list of tuples"""
        if tup[1]:
            return float('.'.join([tup[0], tup[1]]))
        else:
            return int(tup[0])
        
