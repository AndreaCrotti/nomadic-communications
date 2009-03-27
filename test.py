#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by andrea crotti on 2009-03-20.
Copyright (c) 2009 Andrea Crotti Corp. All rights reserved.
"""

import unittest
import re
import random
import glob
import time
from parse_iperf import *
from tester import *

TESTFILES = glob.glob("dataLab/logs/*.txt")

class TestRunner:
    """Putting all together and running the test, saving output with shelve"""
    def __init__(self):
        self.conf = Conf()
        localOs = os.uname() 
        self.testdb = shelve.open("testdb")
        self.conf['iperf']['csv'].set(False)
        self.conf['iperf']['host'].set("localhost")
        self.conf['iperf']['time'].set(5)
        self.iperfOut = IperfOutPlain()
        self.plotter = Plotter("test", "kbs")
            
    def runTest(self, ntimes):
        print "actual configuration is %s, modify %s to change conf" % (self.conf, self.conf.conf_file)
        # for n in range(ntimes):
        r, w, e = os.popen3(str(self.conf['iperf']))
        
        for line in w.readlines():
            self.iperfOut.parse_line(line)
                
        print self.iperfOut.result
        # self.plotter.add_data(self.iperfOut.getValues(), "data test")
        # self.plotter.plot()

class TestIperfOut(unittest.TestCase):
    def setUp(self):
        self.values = {
            "csv"   :
                {
                    "tcp" : ("20090324101545,192.168.0.2,61364,192.168.0.1,5001,3,0.0-5.0,3350528,5360414", {'kbs': '5234.78'}),
                    "udp" : (
                                "20090314193213,172.16.201.131,5001,172.16.201.1,63132,3,0.0-10.0,1312710,1049881,0.838,0,893,0.000,0",
                                {'kbs': '1025.27', 'total': '893', 'jitter': '0.838', 'missed': '0'}
                            )
                },
            "plain" :
                {
                    "tcp" : ("[  3]  0.0- 5.0 sec  3312 KBytes    660 KBytes/sec", {'kbs': 660.0}),
                    "udp" : (
                                "[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)",
                                {'kbs': 1.05, 'jitter': 1.496, 'missed': 0.0, 'total': 893.0}
                            )
                }
        }

    def testCsv(self):
        csv = IperfOutCsv(udp = True)
        val = self.values["csv"]
        self.assertEqual(csv.parse_line(val["udp"][0]), val["udp"][1])
        csv.udp = False
        self.assertEqual(csv.parse_line(val["tcp"][0]), val["tcp"][1])
        # check if both results are present in the final result
        self.assertEqual(csv.result, [val["udp"][1], val["tcp"][1]])
        self.assertEqual(csv.get_values(), ['1025.27', '5234.78'])

    def testPlain(self):
        plain = IperfOutPlain(udp = True)
        val = self.values["plain"]
        self.assertEqual(plain.parse_line(val["udp"][0]), val["udp"][1])
        plain.udp = False
        self.assertEqual(plain.parse_line(val["tcp"][0]), val["tcp"][1])
        self.assertEqual(plain.result, [val["udp"][1], val["tcp"][1]])
        

class TestSize(unittest.TestCase):
    def setUp(self):
        self.small = (Size(102301, 'B'), 99.90)
        
    def testTranslate(self):
        self.assertEqual(self.small[0].translate('K'), self.small[1])
        

def iperfAnalyzer():
    """Generates the configuration, executes the program and plot it"""
    iperf = Plotter("iperf output")
    for f in TESTFILES:
        o = IperfOutput({})

    iperf = Plotter("iperf output")
    for count in range(20):
        i = IperfConf("lts")
        cmd = "iperf " + str(IperfConf("koalawlan"))
        _, w, _ = os.popen3(cmd)
        out = IperfOutput(w, {})
        for x in out.nextResult():
            print x, "\t",  out.result
            iperf.update([x])

class TestConstOpt(unittest.TestCase):
    def setUp(self):
        self.ipregex = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        self.goodIP = "192.2.31.4"
        self.badIp = "23.1.1000.2"
    
    def testSetting(self):
        c = ConstOpt("ip", regex = self.ipregex)
        c.set(self.goodIP)
        self.assertEqual(c.value, self.goodIP)
        self.failUnlessRaises(ValueError, c.set, self.badIp)
    
    def testEq(self):
        self.assertEqual(ConstOpt("prova"), ConstOpt("prova"))

class TestParamOpt(unittest.TestCase):
    def setUp(self):
        self.name = "param"
        self.values = range(10)
        self.good = 3
        self.bad = 11
    
    def testSetting(self):
        p = ParamOpt(self.name, self.good, [self.values])
        self.assertEqual(p.value, self.good)
        self.failUnlessRaises(ValueError, p.set, self.bad)
        
    def testEq(self):
        self.assertEqual(ParamOpt("param", "value", ["value", "value2"]), ParamOpt("param", "value", ["value", "value2"]))
    
class TestBoolOpt(unittest.TestCase):
    def setUp(self):
        self.name = "boolean"
        self.good = True
        self.bad = "true"
    
    def testSetting(self):
        """docstring for testSetting"""
        b = BoolOpt(self.name)
        b.set(self.good)
        self.assertEqual(b.value, self.good)
        self.failUnlessRaises(ValueError, b.set, self.bad)
        
    def testEq(self):
        self.assertEqual(BoolOpt("option", False), BoolOpt("option", False))
        
    
class TestIperfConf(unittest.TestCase):
    """testing iperf configurator"""
    def setUp(self):
        pass
        
class TestSectionConf(unittest.TestCase):
    def setUp(self):
        pass

def testPlotter():
    """docstring for testPlotter"""
    p = Plotter("test", "band")
    p.add_data([50 + random.randrange(5)], "random")
    for x in range(100):
        p.update([50 + random.randrange(5)])
        time.sleep(0.05)
    p.add_data([30 + random.randrange(20)], "random2")
    for x in range(100):
        p.update([30 + random.randrange(20)])
        time.sleep(0.05)
        
    p.add_data([20 + random.randrange(5)], "random3")
    for x in range(100):
        p.update([20 + random.randrange(5)])
        time.sleep(0.05)
        

if __name__ == '__main__':
    # testPlotter()
    # t = TestRunner()
    # t.runTest(10)
    unittest.main()