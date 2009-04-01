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
import ConfigParser
from parse_iperf import *
from tester import *

TESTFILES = glob.glob("dataLab/logs/*.txt")

class TestCnf(unittest.TestCase):
    def setUp(self):
        self.iperf_conf = {
            "speed" : ["1M", "2M"],
            "time" : [1, 10, 20],
            "host" : "lts",
            "format" : "K",
            "interval": [1,2,3]
        }

    def testIperf(self):
        i = IperfConf(self.iperf_conf)
        self.assertEqual(str(i), 'iperf -c lts -i 1 -b 1M -t 1 -f K')
    
    def testApConf(self):
        pass

class TestTestBattery(unittest.TestCase):
    def setUp(self):
        self.test = TestBattery()
        c1 = Configure(self.test.full)
        c2 = Configure(self.test.full)
        c2.conf['iperf']['speed'].set('2M')
        c3 = Configure(self.test.full)
        c3.conf['ap']['speed'].set('2M')
        self.test.battery = [c1, c2, c3]
    
    def testGroup(self):
        self.assertEqual([map(str, x) for x in self.test._group_auto()], 
            [['test --> num_tests 1\niperf --> iperf -f K -c lts -i 3 -b 1G -t 20\nclient --> driver  brand  speed 1M model \nap --> comment  speed 1M ssid nossid ip 23.13.1.41 frag_threshold 256 rts_threshold 256 channel 7', 
            'test --> num_tests 1\niperf --> iperf -f K -c lts -i 3 -b 2M -t 20\nclient --> driver  brand  speed 1M model \nap --> comment  speed 1M ssid nossid ip 23.13.1.41 frag_threshold 256 rts_threshold 256 channel 7'], 
            ['test --> num_tests 1\niperf --> iperf -f K -c lts -i 3 -b 1G -t 20\nclient --> driver  brand  speed 1M model \nap --> comment  speed 2M ssid nossid ip 23.13.1.41 frag_threshold 256 rts_threshold 256 channel 7']])
        

class TestConfigure(unittest.TestCase):
    def setUp(self):
        self.full = TestBattery().full
        self.c = Configure(self.full)
        self.c1 = Configure(self.full)
        self.c1['iperf']['host'].set("server")
        self.c['ap']['speed'].set('11M')
    
    def testNeq(self):
        self.assertEqual(str(self.c - self.c1), "{'iperf': {'host': -c lts}, 'ap': {'speed': speed 11M}}")
        self.assertEqual(str(self.c1 - self.c), "{'iperf': {'host': -c server}, 'ap': {'speed': speed 1M}}")
        self.assertTrue(self.c != self.c1)

# TODO rewrite testIperfOutput
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