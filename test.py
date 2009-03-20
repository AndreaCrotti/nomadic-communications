#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by andrea crotti on 2009-03-20.
Copyright (c) 2009 Andrea Crotti Corp. All rights reserved.
"""

import unittest
import re
from parse_iperf import *

class TestConstOpt(unittest.TestCase):
    def setUp(self):
        self.ipregex = re.compile(r".*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*")
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
        self.assertEqual(ParamOpt(self.name, self.flag, self.good, self.values).value, self.good)
        self.failUnlessRaises(ValueError, ParamOpt, self.name, self.flag, self.bad, self.values)
        
if __name__ == '__main__':
    unittest.main()