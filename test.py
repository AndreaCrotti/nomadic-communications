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
import time
import ConfigParser
from parse_iperf import *
from tester import *

class TestConfiguration(unittest.TestCase):
    def setUp(self):
        c = Configuration("mycodename")
        c["Uno"] = {'a' : 10}
        c["due"] = {'b' : 20}
        print c


class TestCnf(unittest.TestCase):
    def setUp(self):
        self.iperf_conf = {
            "speed" : ["1M", "2M"],
            "time" : [1, 10, 20],
            "host" : "lts",
            "format" : "K",
            "interval": [1,2,3]
        }
        self.iperf_conf2 = {
            "host" : "lprova",
            "format" : "M",
            "interval": 10
        }

    def testIperf(self):
        i = IperfConf(self.iperf_conf)
        i2 = IperfConf(self.iperf_conf2)
        self.assertEqual(str(i), 'iperf -c lts -f K -b 1M -i 1 -t 1')
        # FIXME doesn't keep ordering when adding
        self.assertEqual(str(i + i2), "iperf -c lprova -i 10 -b 1M -t 1 -f M")
    
    def testApConf(self):
        pass

# TODO rewrite testIperfOutput
class TestSize(unittest.TestCase):
    def setUp(self):
        self.small = (Size(102301, 'B'), 99.90)
        
    def testTranslate(self):
        self.assertEqual(self.small[0].translate('K'), self.small[1])
        
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
        self.assertNotEqual(ConstOpt("prova"), ConstOpt("prova1"))

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
        self.assertNotEqual(ParamOpt("param", "value", ["value", "value2"]), ParamOpt("param", "value2", ["value", "value2"]))
    
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