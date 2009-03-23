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
        self.plotter = Plotter("test", "bs")
            
    def runTest(self, ntimes):
        print "actual configuration is %s, modify %s to change conf" % (self.conf, self.conf.conf_file)
        # for n in range(ntimes):
        r, w, e = os.popen3(str(self.conf['iperf']))
        
        for line in w.readlines():
            self.iperfOut.parseLine(line)
                
        print self.iperfOut.result
        # self.plotter.addData(self.iperfOut.getValues(), "data test")
        # self.plotter.plot()

class TestIperfOut(unittest.TestCase):
    def setUp(self):
        self.csvLine = "20090314193213,172.16.201.131,5001,172.16.201.1,63132,3,0.0-10.0,1312710,1049881,0.838,0,893,0.000,0"
        self.csvResult = [{'bs': '1049881', 'jitter': '0.838', 'missed': '0', 'total': '893'}]
        self.plainLine = "[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)"
        self.plainResult = [{'bs': 1.05, 'jitter': 1.496, 'missed': 0.0, 'total': 893.0}]

    def testCsv(self):
        csv = IperfOutCsv()
        csv.parseLine(self.csvLine)
        self.assertEqual(csv.result, self.csvResult)
        self.assertEqual(csv.getValues()[0], self.csvResult[0][csv.value])
    
    def testPlain(self):
        plain = IperfOutPlain()
        plain.parseLine(self.plainLine)
        self.assertEqual(plain.result, self.plainResult)
        

def iperfAnalyzer():
    """Generates the configuration, executes the program and plot it"""
    iperf = Plotter("iperf output")
    for f in TESTFILES:
        o = IperfOutput({})

    iperf = Plotter("iperf output")
    for count in range(20):
        i = IperfConf("lts")
        cmd = "iperf " + str(IperfConf("koalawlan"))
        # print cmd
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
    p.addData([50 + random.randrange(5)], "random")
    for x in range(100):
        p.update([50 + random.randrange(5)])
        time.sleep(0.05)
    p.addData([30 + random.randrange(20)], "random2")
    for x in range(100):
        p.update([30 + random.randrange(20)])
        time.sleep(0.05)
        
    p.addData([20 + random.randrange(5)], "random3")
    for x in range(100):
        p.update([20 + random.randrange(5)])
        time.sleep(0.05)
        

if __name__ == '__main__':
    # testPlotter()
    t = TestRunner()
    t.runTest(10)
    unittest.main()