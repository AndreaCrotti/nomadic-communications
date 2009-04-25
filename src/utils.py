import sys, os, subprocess
import paramiko
import logging
import ConfigParser
import re

from vars import *
from errors import *
from config import Configuration

def latex_table(text, length):
    aligns = "{" + "l || " + "|".join(["c"] * (length -1)) + "}"
    begin = r"\begin{tabular}" + aligns
    end = r"\end{tabular}"
    return "\n".join([begin, text, end])

def tests_to_latex(tests, pars):
    lines = "\n".join([t.latex_line(pars) for t in tests])
    return latex_table(lines, len(pars))

def get_codename(test_file):
    """
    Getting the codename from a whatever, using global variables
    """
    for el in RESULTS.values():
        # Unreliable but working pretty well
        reg = re.compile("(.*)".join(el.split("%s")))
        found = r.search(test_file)
        if found:
            return found.groups()[0]
    return None

def get_tests_configs(user):
    codenames = get_tests(user)
    base = os.path.join("..", ROOT %  user)
    configs = []
    for code in codenames:
        full_conf = os.path.join(base, "full_conf", RESULTS["full_conf"] % code)
        configs.append(Configuration(full_conf, code))
    return configs

def get_tests(user):
    """
        Get the tests done by the user, loading file
        completed in the root result folder
    """
    completed = os.path.join("..", ROOT % user, COMPLETED)
    try:
        return open(completed).read().splitlines()
    except IOError:
        print "not possible to find the completed tests file"
        

class ParamikoFilter(logging.Filter):
    def __init__(self, name='root'):
        """ By default everything is left passing"""
        logging.Filter.__init__(self, name)
    
    def filter(self, rec):
        return self.name == 'root'

def config_to_dict(conf_file):
    c = ConfigParser.ConfigParser()
    c.readfp(open(conf_file))
    dic = {}
    for name in c.sections():
        dic[name] = {}
        for opt in c.options(name):
            dic[name][opt] = c.get(name, opt)
    logging.debug("getting %s" % dic)
    return dic

def get_mon():
    iperf = ("iperf", "-s -u")
    tcpdump = ("nohup tcpdump", "-i eth0 -c 1000 -w")
    ls = ("ls", "-lR")
    r = RemoteCommand(outfile = "mon.dump", server=True)
    u = config_to_dict("remotes.ini")['monitor']
    r.connect(**u)
    r.run_command(*tcpdump)
    return r

class RemoteCommand(object):
    """Incapsulating the need of launching commands and
    getting the resulting output"""
    def __init__(self, outfile="dump", server=False):
        self.outfile = outfile
        self.ssh = paramiko.SSHClient()
        self.server = server
        # this should be enough for the server key
        self.ssh.load_system_host_keys()
        self.killcmd = None

    def connect(self, **kw):
        try:
            # so I also take it off the dictionary
            host = kw.pop('host')
        except KeyError:
            logging.error("Host key is really needed")
        if kw.has_key('port'):
            # FIXME int conversion not enough?
            # an int is needed for port number
            kw['port'] = int(kw['port'])
        else:
            
            try:
                # the connection stays open until close()
                self.ssh.connect(host, **kw)
            except Exception, e:
                msg = "Not able to connect to %s for reason %s" % (host, e)
                raise NetworkError(msg)

    def run_command(self, cmd):
        logging.info("running command %s" % cmd)
        self.ssh.exec_command(cmd)

    def run_server(self, cmd, args):
        # the kill command must not be complete
        # FIXME using the PID instead
        self.killcmd = cmd
        command = " ".join([cmd, args, "> %s" % self.outfile])
        if self.server:
            # in this way I get back the control
            command += " &"
        logging.info("running command %s" % command)
        print("running command %s" % command)
        _,o,e = self.ssh.exec_command(command)
        out, err = o.read(), e.read()
        if out:
            print out
            logging.info(out)
        if err:
            print err
            logging.error(err)
    
    def get_output(self, remote_file):
        ftp = self.ssh.open_sftp()
        logging.info("downloading file %s to %s" % (self.outfile, remote_file))
        ftp.get(self.outfile, remote_file)
        
    def close(self, kill=False):
        if self.killcmd:
            kill = "killall %s" % self.killcmd
            logging.info("executing %s" % kill)
            if kill:
                _, o, e = self.ssh.exec_command(kill)
                out, err, = o.read(), e.read()
                if err:
                    logging.error(e.read())
                if out:
                    logging.info(o.read())
                # close and kill the command if still running
        self.ssh.close()

def send_command(host, command):
    """Sending a command and returning the output"""
    ssh = paramiko.SSHClient()
    # this should be always enough, otherwise add it manually
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username="root", password="condor", port=22) #pkey=open("/Users/andrea/.ssh/andrea").read(), 
    _,o,e = ssh.exec_command(command)
    ssh.close()
    return o.read()
    
def tuple_to_num(tup):
    """Taking float numbers in a list of tuples"""
    if tup[1]:
        return float('.'.join([tup[0], tup[1]]))
    else:
        return int(tup[0])

def banner(text, sym="*"):
    start = end = sym * 40
    print "\n".join(map(lambda x: x.center(50), [start, text, end]))

# TODO write a better remote host checking
def to_remote(cmd):
    print "==>\t" + cmd

def to_local(cmd):
    print "!!\t" + cmd

    
# TODO avoid returning booleans, using exception handling!!
def check_remote(host, user = None, command = ""):
    """Checking the remote access to a host, optionally
    with user user (useful to check root access)"""
    if user:
        p = subprocess.Popen(remote(host, "id"), stdout = subprocess.PIPE, shell=True)
        out = p.stdout.read()
        if user in out:
            print "yes you are the root"
            return True
        else:
            print "no dude"
            return False
    else:
        return (subprocess.Popen(remote(host, 'ls'), shell=True, stdout = subprocess.PIPE).wait() == 0)

# FIXME wait until the end, spawn the process maybe
def play(message):
    """Plays a wav file given in message"""
    if sys.platform == 'darwin':
        os.popen("playsound %s" % message)
    else:
        os.popen("aplay %s" % message)

class MenuMaker(object):
    """Generates a nice menu"""
    def __init__(self, choices, key = "val"):
        self.choices = choices
        self.key = key
        self.default = self.choices[0]
        self.menu = dict(enumerate(self.choices))
        
    def __str__(self):
        return '\n'.join([str(i) + ")\t" + str(self.menu[i]) for i in range(len(self.choices))])
    
    def __getitem__(self, idx):
        if self.key == "val":
            return self.menu[idx]
        elif self.key == 'idx':
            return idx
        
# TODO Use dialog if available
def menu_set(menu):
    while True:
        print str(menu)
        val = raw_input("make a choice (default %s):\n\n" % str(menu.default))
        if val == '':
            if menu.key == "val":
                return self.default
            else:
                return 0
        else:
            try:
                return menu[int(val)]
            except KeyError:
                continue
            except ValueError:
                print "you must give integer input"
                continue


class Size(object):
    """ Converting from one unit misure to the other """
    def __init__(self, value, unit = 'B'):
        self.value = value
        self.units = ['B', 'K', 'M', 'G']
        if unit not in self.units:
            raise ValueError, "unit must be in " + str(self.units)
        self.unit = unit

    def translate(self, unit):
        """Returns the rounded translation in a different unit measure"""
        if unit not in self.units:
            raise ValueError, "can only choose " + self.units
        else:
            offset = self.units.index(self.unit) - self.units.index(unit)
            return round(self.value * (pow(1024, offset)), 2)
        
    def __str__(self):
        return " ".join([str(self.value), self.unit])