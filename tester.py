#!/usr/bin/env python
import ConfigParser
import os
import re
import sys
from copy import deepcopy
from parse_iperf import *

def interactive():
    c = Configure()
    c.make_conf()


class Cnf:
    def __init__(self, name):
        self.to_conf()
    
    def __repr__(self):
        return ' '.join([repr(val) for val in self.conf.values()])

    def __getitem__(self, idx):
        return self.conf[idx]

    def to_conf(self):
        self.conf = {}
        for key in self.options.keys():
            v = self.raw_conf[key]
            if type(v) == list:
                # =====================================================
                # = IMPORTANT, default value is the first in the list =
                # =====================================================
                self.conf[key] = ParamOpt(self.options[key], v[0], v)
            else:
                self.conf[key] = ConstOpt(self.options[key], v)
    
    def params(self):
        return [k for k in self.conf.keys() if isinstance(self.conf[k], ParamOpt)]
    
class IperfConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        self.options = {
            "speed" : "-b",
            "host"  : "-c",
            "time"  : "-t",
            "format" : "-f"
        }
        Cnf.__init__(self, "iperf")

    def __repr__(self):
        return "iperf " + Cnf.__repr__(self)

class ApConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        par = ["speed", "rts_threshold", "frag_threshold"]
        # no need of flag
        self.options = dict(zip(par, par))
        Cnf.__init__(self, "ap")

class NicConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        self.options = dict(speed = "speed")
        Cnf.__init__(self, "nic")

class TestConf(Cnf):
    def __init__(self, conf):
        self.raw_conf = conf
        self.options = dict(num_tests = "num_tests")
        Cnf.__init__(self, "test")


class Configure:
    conf_file = 'config.ini'
    def __init__(self):
        self.reader = ConfigParser.ConfigParser()
        self.reader.readfp(open(self.conf_file))
        # setting also the order in this way,
        self.conf = {
            "iperf" : IperfConf(self.get_conf("iperf")),
            "ap"    : ApConf(self.get_conf("ap")),
            "nic"   : NicConf(self.get_conf("nic"))
        }
        self.sections = ParamOpt("sections", "iperf", self.conf.keys()) 

    def make_conf(self):
        print "starting interactive configuration"
        self.sections.iter_set()
        # o = self.conf[self.sections.value].options.keys()
        params = self.conf[self.sections.value].params()
        opts = ParamOpt("parameters", params[0], params)
        opts.iter_set()
        for c in self.scan_conf(self.sections.value, opts.value):
            print c
        

    def get_conf(self, section):
        conf = {}
        for k in self.reader.options(section):
            val = self.reader.get(section, k)
            if val.find(',') >= 0:  # it's a list
                conf[k] = val.replace(' ','').split(',')
            else:
                conf[k] = val
        return conf
    
    def scan_conf(self, section, param):
        """Only one parameter at a time can change"""
        for x in self.conf[section][param].get_next():
            self.conf[section][param].set(x)
            yield self.conf
            
if __name__ == '__main__':
    interactive()
