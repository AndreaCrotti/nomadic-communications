# encoding: utf-8
import sys
# FIXME better way to handle module importing
sys.path.append("../src")
import unittest
import subprocess
import time
from utils import *

class TestUtils(unittest.TestCase):
    """docstring for TestUtils"""
    def setUp(self):
        """docstring for setUp"""
        self.cmd = RemoteCommand()
        self.remotes = load_remote_config("../remotes.ini")
        print self.remotes

class TestSize(unittest.TestCase):
    def setUp(self):
        # Just put in this list all the cases you want to examine
        self.equals = [
                        ((Size(1, 'MB'), Size(1024, 'KB')),
                        (Size(1, 'Mb'), Size(128, 'KB')))]
        
    def testTranslate(self):
        for t in self.equals:
            for s1, s2 in t:
                self.assertEqual(s1.value, s2.translate(s1.unit))

class TestTimer(unittest.TestCase):
    """Testing the timer class,
    giving some possible translations to do"""
    
    def setUp(self):
        self.equals = [
            (Timer(100), (0,1,40)),
            (Timer(20), (0,0,20)),
            (Timer(3600), (1,0,0))
        ]
        self.vars = ('h', 'm', 's')
    
    def testEqs(self):
        for ti in self.equals:
            t = ti[0]
            for val, var in zip(ti[1], self.vars):
                self.assertEqual(val, getattr(t, var))

if __name__ == '__main__':
    unittest.main()