#!/usr/bin/env python
import ConfigParser
import os
import re
import sys
from copy import deepcopy

conf_file = 'config.ini'

def get_conf():
    reader = ConfigParser.ConfigParser()
    reader.readfp(open(conf_file))
    conf = {}
    keys = ["speeds", "rts_threshold", "frag_threshold", "num_tests", "time", "host", "type"]
    for k in keys:
        val = reader.get('parameters', k)
        if val.find(',') >= 0:  # it's a list
            conf[k] = val.replace(' ','').split(',')
        else:
            conf[k] = val
    return conf

def scan_conf(conf, param):
    """Scanning over a parameter setting fixed the others"""
    lists = [ key for key in conf.keys() if type(conf[key]) == list and key != param ]
    for p in lists:
        conf[p] = raw_input("set a value for %s:" % p)
    print "\n\n"
    for el in conf[param]:
        conf[param] = el
        yield conf
        
for x in scan_conf(get_conf(), "speeds"):
    print x