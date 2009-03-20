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
        self.assertEqual(ConstOpt("ip", self.goodIP, self.ipregex).value, self.goodIP)
        self.failUnlessRaises(ValueError, ConstOpt, "ip", self.badIp, self.ipregex)

class TestParamOpt(unittest.TestCase):
    """docstring for TestParamOpt(unittest.TestCase)"""
    def setUp(self):
        """docstring for setUp"""
        self.name = "param"
        self.flag = "-p"
        self.values = range(10)
        self.good = 3
        self.bad = 11
    
    def testSetting(self):
        """docstring for testSetting"""
        self.assertEqual(ParamOpt(self.name, self.good, self.values).value, self.good)
        self.failUnlessRaises(ValueError, ParamOpt, self.flag, self.bad, self.values)
        
class TestIperfConf(unittest.TestCase):
    """testing iperf configurator"""
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