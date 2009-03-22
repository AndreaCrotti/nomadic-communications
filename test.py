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
from parse_iperf import *

TESTFILES = glob.glob("dataLab/logs/*.txt")

class TestIperfOut(unittest.TestCase):
    def setUp(self):
        self.csvLine = """"20090314193213,172.16.201.1,63132,172.16.201.131,5001,3,0.0-10.0,1312710,1048592
        20090314193213,172.16.201.131,5001,172.16.201.1,63132,3,0.0-10.0,1312710,1049881,0.838,0,893,0.000,0"""
        # self.csvResult = 
        self.plainLine = "[  3]  0.0-10.0 sec  1.25 MBytes  1.05 Mbits/sec  1.496 ms    0/  893 (0%)"
    
    def testCsv(self):
        pass

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
    p = Plotter("test")
    # using * to autoscale one of the variables
    p.plotter.set_range('yrange', '[0:*]')
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
    unittest.main()