import sys, os
import StringIO
sys.path.append('/Library/Python/2.5/site-packages/Mako-0.2.4-py2.5.egg/')
sys.path.append('../src')
from vars import *
from utils import get_tests

from mako.template import Template
from mako.runtime import Context
# TODO using the lookup to find out whatever is needed
from mako.lookup import TemplateLookup

output_encoding = 'utf-8'

for t in get_tests("andrea"):
    dic = {"graph_file" : t, "codename" : t}
    graph = Template(filename = "templates/graph.tex").render(**dic)
    test = Template(filename = "templates/test.tex")
    print test.render(graph = graph, codename = t, comment = "nessuno")