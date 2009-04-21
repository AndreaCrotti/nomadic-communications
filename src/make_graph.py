#!/usr/bin/env python
# intended to be a separated tool

import sys, os
import getopt
from analyze import *
from parse_iperf import *
# TODO only pass the configuration name and user
from vars import *

OUTPUT = "graph.eps"
NAME = "mytest"

def usage():
    print """
    ./make_graph.py [-n name] [-c <config>] [-o <output_file>] file1 file2...
    This script takes a list of files (which are the iperf output).
    Then it automatically detects if it's the server or the client and parse it
    accordingly.
    A graph is generated with the related functions
    """
    sys.exit(0)

def make_plot(files):
    p = Plotter(NAME, 'kbs')
    for test in files:
        base = os.path.basename(test)
        code = base.split('.')[0]
        if 'client' in base:
            i = IperfClientPlain()
            i.parse_file(open(test))
        if 'server' in base:
            i = IperfServer()
            i.parse_file(open(test))

        res = i.get_values()
        print "adding data of %s: %s" % (code, res)
        p.add_data(res, code)
    p.plot()
    
if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], "c:o:n:")
    for o in opts:
        if 'c' in o:
            load_conf(o[1])
        if 'o' in o:
            global OUTPUT
            OUTPUT = o[1]
        if 'n' in o:
            global NAME
            NAME = o[1]
    if not args:
        usage()
    make_plot(args)
