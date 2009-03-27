#!/usr/bin/env python
import ConfigParser
import os
import re
import sys
from copy import deepcopy
from parse_iperf import *

class IperfConf:
    def __init__(self, conf):
        self.conf = conf
        self.options = {
            "speed" : "-b",
            "host"  : "-c",
            "time"  : "-t"
        }
        self.to_conf()

    def to_conf(self):
        iperf_cmd = {}
        for key in self.options.keys():
            v = self.conf[key]
            if type(v) == list:
                iperf_cmd[key] = ParamOpt(self.options[key], v[0], v)
            else:
                iperf_cmd[key] = ConstOpt(self.options[key], v)
        self.cmd = SectionConf("iperf", iperf_cmd)
        
    def __repr__(self):
        return repr(self.cmd)

class Configure:
    conf_file = 'config.ini'
    def __init__(self):
        self.reader = ConfigParser.ConfigParser()
        self.reader.readfp(open(self.conf_file))
        # setting also the order in this way,
        self.keys = {
            "parameters" : ["speed", "rts_threshold", "frag_threshold", "num_tests", "time", "host", "type"],
            "ap"         : ["ip", "ssid", "channel", "model", "comment"]
        }
        self.config = {
            "parameters" : self.get_conf("parameters"),
            "ap"     : self.get_conf("ap")
        }
        self.iperf_cmd = IperfConf(self.config["parameters"])

    def get_conf(self, section):
        conf = {}
        for k in self.keys[section]:
            val = self.reader.get(section, k)
            if val.find(',') >= 0:  # it's a list
                conf[k] = val.replace(' ','').split(',')
            else:
                conf[k] = val
        return conf
    
    def scan_conf(self, param):
        """Scan over possible configurations, only parameters can change, other things are only set statically"""
        cnf = self.config[section]
        lists = [ key for key in cnf.keys() if type(cnf[key]) == list and key != param ]
        for p in lists:
            cnf[p] = raw_input("set a value for %s, possible values are %s:" % (p, cnf[p]))
        print "\n\n"
        for el in cnf[param]:
            cnf[param] = el
            yield cnf
