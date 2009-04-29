import sys, os, subprocess
import paramiko
import logging
import ConfigParser
import re
from string import lower, upper

from vars import *
from errors import *
from config import Configuration

# ===================
# = Latex utilities =
# ===================
def latex_table(text, length):
    aligns = "{" + "l || " + "|".join(["c"] * (length -1)) + "}"
    begin = r"\begin{tabular}" + aligns
    end = r"\end{tabular}"
    return "\n".join([begin, text, end])

def tests_to_latex(tests, pars):
    lines = "\n".join([t.latex_line(pars) for t in tests])
    return latex_table(lines, len(pars))

# ===========================
# = Test managing utilities =
# ===========================
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

class RemoteCommand(object):
    """Incapsulating the need of launching commands and
    getting the resulting output.
    It's important that you need to have your host already
    in ~.ssh/known_hosts, otherwise it will refuse
    to connect even if user/password are correct
    """
    def __init__(self, outfile="dump", server=False):
        self.outfile = outfile
        self.ssh = paramiko.SSHClient()
        self.server = server
        # loading knows hosts
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
    
def tuple_to_num(tup):
    """Taking float numbers in a list of tuples"""
    if tup[1]:
        return float('.'.join([tup[0], tup[1]]))
    else:
        return int(tup[0])

def banner(text, sym="*"):
    start = end = sym * 40
    print "\n".join(map(lambda x: x.center(50), [start, text, end]))


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

class Timer(object):
    def __init__(self, value):
        self.h = 0
        self.m, self.sec = divmod(value, 60)
        if self.m > 0:
            self.h, self.m = divmod(self.m, 60)
        
    def __repr__(self):
        return str(self)

    def __str__(self):
        s = ""
        if self.h > 0:
            s += "%d hour, " % self.h
        if self.m > 0:
            s += "%d minute, " % self.m
        s += "%d second\t" % self.sec
        return s

def get_speed(speed, unit):
    """Gets the speed out of a string (1M, 2g for example)
    converts it into unit if necessary
    """
    reg = re.compile(r'([\d.]+)(\w+)')
    s, u = reg.match(speed).groups()
    return Size(s, u).translate(unit)

class Size(object):
    """ Converting from one unit misure to the other """
    def __init__(self, value, unit = 'B'):
        """Gets a value which represents a float, could
        be int or even string"""
        self.value = float(value)
        self.low = ['b', 'Kb', 'Mb', 'Gb']
        self.high = [''.join(map(upper, s)) for s in self.low]
        self.units = dict(zip(self.low, range(0, len(self.low)*10, 10)) +\
            zip(self.high, range(3, len(self.high)*10, 10)))
        
        self._check_unit(unit)
        self.unit = unit
        
    def _check_unit(self, unit):
        """Check if correct unit, raises ValueError
        exception"""
        if unit not in self.units.keys():
            raise ValueError, "can only choose " + str(self.units.keys())

    def translate(self, unit):
        """Returns the rounded translation in a different unit measure
        It DOESN'T return a new Size object but the just the value
        """
        self._check_unit(unit)
        # FIXME attention to equal named variables
        offset = self.units[self.unit] - self.units[unit]
        return round(self.value * (pow(2, offset)))
        
    def __str__(self):
        return " ".join([str(self.value), self.unit])
    
    def __repr__(self):
        return str(self)
        
class Speed(Size):
    def __init__(self, value, unit):
        Size.__init__(self, value, unit)
    
    def __str__(self):
        return Size.__str__(self) + "/s"