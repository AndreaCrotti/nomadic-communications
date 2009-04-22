#!/usr/bin/env python
# encoding: utf-8


import unittest
import re
import random
import time
import ConfigParser
import sys
import StringIO

sys.path.append('..')
from parse_iperf import *
from opts import *
from config import *

class TestConfiguration(unittest.TestCase):
    def setUp(self):
        conf1 = '[iperf]\nspeed = 11M\n\n[ap]\nspeed = 1M'
        conf2 = '[iperf]\nspeed = 1M\n\n[ap]\nspeed = 2M'
        t1 = "testconf1.ini"
        t2 = "testconf2.ini"
        open(t1, 'w').write(conf1)
        open(t2, 'w').write(conf2)
        self.c1 = Configuration(t1)
        self.c2 = Configuration(t2)
        
    def testSub(self):
        self.assertEqual(str(self.c1 - self.c2), 'iperf:\t iperf -b 1M\nap:\t speed 2M')
    
    # TODO implement tests for all ohter important methods

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
        self.assertEqual(str(i), 'iperf -c lts -b 1M -t 1 -i 1 -f K')
        self.assertEqual(str(i + i2), 'iperf -c lprova -b 1M -t 1 -i 10 -f M')
        self.assertEqual(str(i - i2), 'iperf -c lprova -b 1M -t 1 -i 10 -f M')
    
    def testApConf(self):
        pass

class TestIperfClient(unittest.TestCase):
    def setUp(self):
        self.plain = """
------------------------------------------------------------
Client connecting to 192.168.1.1, UDP port 5001
Sending 1470 byte datagrams
UDP buffer size: 9.00 KByte (default)
------------------------------------------------------------
[  3] local 192.168.1.23 port 52876 connected with 192.168.1.1 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0- 5.0 sec    612 KBytes    122 KBytes/sec
[ ID] Interval       Transfer     Bandwidth
[  3]  5.0-10.0 sec    610 KBytes    122 KBytes/sec
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  1223 KBytes    122 KBytes/sec
[  3] Sent 852 datagrams
[  3] Server Report:
[ ID] Interval       Transfer     Bandwidth       Jitter   Lost/Total Datagrams
[  3]  0.0-6579.6 sec  1223 KBytes  0.19 KBytes/sec  0.006 ms    0/  852 (0%)
"""
        self.plain_res = {'avg': 0.19, 'jitter': 0.0060000000000000001, 'missed': 0, 'transfer': 1223, 'values': [122, 122, 122], 'total': 852}
        
    def testPlain(self):
        i = IperfClientPlain()
        for line in self.plain.splitlines():
            i.parse_line(line)
        self.assertEqual(i.result, self.plain_res)
        # now testing with parse_line
        i2 = IperfClientPlain()
        # not creating a real file
        f = StringIO.StringIO(self.plain)
        i2.parse_file(f)
        self.assertEqual(i2.result, self.plain_res)
        
    
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
        c = ConstOpt("ip", value = self.goodIP, regex = self.ipregex)
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
    
    def testInit(self):
        # TODO check __init__ also
        pass
        # self.failUnlessRaises(ValueError, ParamOpt.__init__, self.name, self.bad, self.values)

    def testSetting(self):
        p = ParamOpt(self.name, self.good, self.values)
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
    unittest.main()