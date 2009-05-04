#!/usr/bin/env python
# Useful script to insert source code
# in the latex relation, using mako + pygment + inspect

import sys
import inspect
import logging
from mako.template import Template

# FIXME find a better way to handle source
sys.path.append('../src')

def get_code(objcode):
    try:
	mod = __import__(objcode)
    except ImportError:
	logging.error("could not find %s" % objcode)
	sys.exit(1)    
    else:
        return inspect.getsource(mod)

if __name__ == '__main__':
    get_code(sys.argv[1])
