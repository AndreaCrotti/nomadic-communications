#!/usr/bin/env python
# encoding: utf-8

import os
import re
import sys
import subprocess
import shutil
import logging

# FIXME: avoid such a long list of imports?
from glob import glob
from getopt import getopt
from src.parse_iperf import *
from src.config import *
from src.utils import *
from src.opts import *
from src.vars import *
from src.analyze import *
from src.errors import *

# global flags
SIMULATE = False
VERBOSE = False
LIST = False

# exit codes FIXME, avoid it use exceptions
BADHOST = 1
BADCONF = 2

# CHANGE here the level of verbosity
logging.basicConfig(stream=sys.stdout)
# to avoid extra modules logging
logging.getLogger().addFilter(logging.Filter("root"))

def get_res(root, code):
    """Returns the dictionary of results paths"""
    paths = [ os.path.join(root, k, val % code) for k, val in RESULTS.iteritems() ]
    return dict(zip(RESULTS.keys(), paths))

class TestBattery(object):
    def __init__(self, username):
        try:
            # maybe need to close also somewhere
            self.conf_file = DEFAULT
        except IOError:
            logging.error("unable to find default configuration in %s, quitting" 
                % self.conf_file)
            sys.exit(BADCONF)

        self.default_conf = Configuration(self.conf_file, codename = "default")
        self.user_conf = Configuration(USER_CONFS % username, codename = username)
        # monitoring informations must stay in user_conf
        self.conf = self.default_conf + self.user_conf
        self.conf.username = "merged"
        # list of all possible configs stored, not opening directly here
        self.test_configs = glob(CONFIGS % "*")
        self.battery = []
        # dictionary containing absolute paths for the results
        self.analyzer_client = IperfClientPlain()
        self.analyzer_server = IperfServer()
        self.root = ROOT % username
        self.remotes = config_to_dict(REMOTES)

    def is_consistent(self, conf):
        """Checking if configuration loaded is consistent with default configuration"""
        for sec in conf.keys():
            if sec not in self.conf.keys():
                logging.info("section %s not found, skipping it" % str(sec))
            else:
                for opt in conf[sec].keys():
                    if opt not in self.conf[sec].keys():
                        print "option %s not found, skipping it" % str(opt)
                    else:
                        # TODO add a sanity check for consistency checking over the merged conf
                        param = self.conf[sec].conf[opt]
                        if not(param.valid(conf[sec].conf[opt].value)):
                            print "option %s not valid %s \n" % (opt, param.choices())
                            return False
        return True
    
    def load_conf(self, conf_file, codename):
        """Loads a configuration from conf_file merging it with
        the default configuration"""
        # the codename is given from the conf_file
        cnf = Configuration(conf_file, codename)
        if self.is_consistent(cnf):
            merged = self.conf + cnf
            if merged in self.battery:      # this works only if == defined correctly
                print "you have already loaded the configuration in %s, not adding" % conf_file
            else:
                logging.info("adding configuration in %s" % conf_file)
                self.battery.append(merged)
        else:
            print "error in %s, please correct the values" % conf_file

    def load_configs(self, configs = []):
        name = lambda x: re.search(r"configs/(.*?).ini", x).groups()[0]
        if not configs:
            configs = self.test_configs
        for conf in configs:
            codename = name(conf)
            self.load_conf(conf, codename)
    
    def summary(self):
        """Prints the summary of the tests that we will execute"""
        for i, test in enumerate(self.battery):
            print str(i) + "):\t" + test.codename + "\n"

    def make_subtree(self, root, dirs):
        if not os.path.exists(root):
            os.mkdir(root)
            for d in dirs:
                os.mkdir(os.path.join(root, d))
            # creating a new empty file
            open(os.path.join(root, COMPLETED), 'w')

    def pre_run(self):
        if LIST:
            # FIXME not printing when not batch mode
            for num, conf in enumerate(self.test_configs):
                print "%d) CONFIGURATION %s\n%s" % (num, conf, open(conf).read())
                print "\n"
            return
        
        i = 0
        self.make_subtree(self.root, RESULTS.iterkeys())
        compl_file = os.path.join(self.root, COMPLETED)
        try:
            completed = map(lambda x: CONFIGS % x, open(compl_file).read().splitlines())
        except IOError:
            # loading everything if not present
            open(compl_file, 'w')
            self.load_configs()
        else:
            diff = list(set(self.test_configs).difference(completed))
            diff.sort()
            # I only load the missing configs ordered
            self.load_configs(diff)
            self.summary()

    def run(self):
        print "This test battery will run in %s" % self.tot_time()
        i = 0
        # Refactor run() code
        while i < len(self.battery):
            if SIMULATE:
                print "setting minimal timings"
                self.battery[i]['iperf']['time'].set("10")
                self.battery[i]['iperf']['interval'].set("1")
                
            server = ("iperf", "-s -u -f K -i " + self.battery[i]["iperf"]["interval"].value)
            # This shows that I could even have different monitors for different tests
            monitor = self.battery[i]['monitor'].get_tuple()
            mon_cmd = "ssh " + self.battery[i]['monitor']['host'].value + " \"" + str(self.battery[i]['monitor']) + " " + DUMP + "\" &"
            srv = RemoteCommand(outfile = SERVER_RESULT, server=True)
            mon = RemoteCommand(outfile = DUMP, server=True)

            try:
                srv.connect(**self.remotes['server'])
                mon.connect(**self.remotes['monitor'])
            except NetworkError, e:
                logging.error("not able to start the server or monitor, check your configuration")
                # having an exit here I would not need to put an else
                sys.exit(BADHOST)

            except KeyboardInterrupt:
                logging.info("restarting from same test")
                continue
            
            srv.run_server(*server)
            # mon.run_command(*monitor)
            print "running as monitor %s" % mon_cmd
            subprocess.Popen(mon_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            banner("TEST %s:\n" % self.battery[i].codename, sym="=")
            try:
                # better handle it here not inside the test itself
                self.run_test(self.battery[i])
            except KeyboardInterrupt:
                a = raw_input("last test canceled, (s)kip or (r)estart or (q)uit the test session:\n")
                if a == 'q':
                    sys.exit(0)
                elif a == 's':
                    i += 1
            else:
                srv.get_output(SERVER_RESULT)
                # getting the output anyway even if launched outside paramiko
                mon.get_output(DUMP)
                if not SIMULATE:
                    self.write_results(self.battery[i])
                    self.analyze(self.battery[i])
                    open(os.path.join(self.root, COMPLETED), 'a').write(self.battery[i].codename + "\n")
                logging.info("test %s done" % self.battery[i].codename)
                i += 1
            finally:
                srv.run_command("rm %s" % SERVER_RESULT)
                mon.run_command("rm %s" % DUMP)
                # always closing the ssh connections (and killing commands also)
                srv.close(kill=True)
                mon.close(kill=False)

    def run_test(self, test):
        """
        Running one single test, plotting the results if gnuplot availble
        and saving the results in a directory structure
        """
        monitor = test.conf['monitor']
        print test
        cmd = str(test['iperf'])
        raw_input("Press any key when ready:\n")
        print "test started, hold on for %s" % str(Timer(int(test['iperf']['time'].value)))
        # automatically writes the output to the right place, kind of magic of subprocess
        proc = subprocess.Popen(cmd, shell=True, stdout=open(CLIENT_RESULT,'w'), stderr=subprocess.PIPE)
        if re.search("did not receive ack", proc.stderr.read()):
            print "host %s not responding, quitting the test" % self.conf['iperf']['host']
            sys.exit(BADHOST)
    
    def write_results(self, test):
        """Finally writes the results of the test in the right directories"""
        res_dict = get_res(self.root, test.codename)
        # TODO check that they are already there
        shutil.move(DUMP, res_dict["dump"])
        shutil.move(CLIENT_RESULT, res_dict["iperf_client"])
        shutil.move(SERVER_RESULT, res_dict["iperf_server"])
        print "wrote results on %s, %s, %s"\
            % (res_dict["dump"], res_dict["iperf_client"], res_dict["iperf_server"])
        test.to_ini(open(res_dict["full_conf"], 'w'))
        
    def analyze(self, test):
        """Analyze the results plotting"""
        # Adding safety checks
        plot_conf = config_to_dict(GNUPLOT_CONF)['plot']
        res_dict = get_res(self.root, test.codename)
        self.analyzer_client.parse_file(open(res_dict["iperf_client"], 'r'))
        self.analyzer_server.parse_file(open(res_dict["iperf_server"], 'r'))
        results = {
            "client" : self.analyzer_client.get_values(),
            "server" : self.analyzer_server.get_values(),
            # "jitter" : self.analyzer_server.get_values(field = 'jitter')
        }
        # FIXME not working anymore
        for k in results.keys():
            if plot_conf.has_key(k):
                print "plotting %s" % str(plot_conf[k])
        # self.plot({"client" : self.analyzer.get_values(), "server" : self.analyzer_server.get_values()}, test.codename, res_dict["graphs"])
        

    def plot(self, results, codename, filename):
        """Plots and writes the graph generated to filename"""
        plotter = Plotter("testing", "kbs")
        for key, val in results.iteritems():
            plotter.add_data(val)
        plotter.plot()
        plotter.save(filename)

    def tot_time(self):
        tot = sum([i.get_time() for i in self.battery])
        return Timer(tot)

    def batch(self):
        """Automatic run of the tests"""
        self.pre_run()
        self.run()

def usage():
    print """
    ./tester.py [-s|--simulate] <user> <conf1> <conf2>...
    if no file are given in input it loads the configuration files configs/test_\d\w.ini
    user is mandatory and will pick up the configuration from userconfs/*.ini
    """
    sys.exit(0)

if __name__ == '__main__':
    # TODO implementing a test cleaner
    opts, args = getopt.getopt(sys.argv[1:], 
        'cvshdl', ['verbose', 'simulate', 'help', 'clean', 'debug', 'list'])
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()

        if o in ('-d', '--debug'):
            # Not functional programming
            logging.getLogger().setLevel(logging.DEBUG)

        if o in ('-v', '--verbose'):
            logging.getLogger().setLevel(logging.INFO)

        if o in ('-s', '--simulate'):
            SIMULATE = True
        
        if o in ('-l', '--list'):
            LIST = True

    # we can pass as many configs files as you want or just let
    # the program look for them automatically
    if args:
        name = args[0]
        if not(os.path.exists(USER_CONFS % name)):
            print "no configuration for %s" % name
            sys.exit(BADCONF)
        else:
            t = TestBattery(name)
            if args[1:]:
                for conf_file in args[1:]:  # all the others could be conf
                    # FIXME ugly hardcoding of file path
                    t.load_conf(conf_file, conf_file.split(".")[0].split("/")[1])
                t.run()
            else:
                t.batch()
    else:
        usage()
