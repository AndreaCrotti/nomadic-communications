import sys, os, subprocess

def clear():
    """Clear the terminal screen, it should be portable in this way"""
    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')

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
    

def remote(host, command):
    """Making a remote command"""
    return " ".join(["ssh", host, command])

# FIXME wait until the end, spawn the process maybe
def play(message):
    """Plays a wav file given in message"""
    if sys.platform == 'darwin':
        os.popen("playsound %s" % message)
    else:
        os.popen("aplay %s" % message)

class MenuMaker:
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


class Size:
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