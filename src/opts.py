import re

# ================================
# = Classes for handling options =
# ================================
class Opt:
    """General class for options, generates a ValueError exception whenever
    trying to set a value which is not feasible for the option"""
    def __init__(self, name, value = None):
        self.name = name
        self.set(value)
    
    def __str__(self):
        if not self.setted:
            return ''
        else:
            if not self.value:
                return self.name
            else:
                return (self.name + " " + str(self.value))
            
    def __repr__(self):
        return str(self)
    
    def __eq__(self, other):
        """checking equality of option types, also type must be equal"""
        return self.name == other.name and self.value == other.value
    
    def __ne__(self, other):
        return not(self == other)

    def unset(self):
        """Unset the option, to disable representation"""
        self.setted = False

    def set(self, value):
        """Setting the value only if validity check is passed"""
        self.setted = True
        if self.valid(value):
            self.value = value
        else:
            raise ValueError, self.choices()

class BoolOpt(Opt):
    """Boolean option, if not set just give the null string"""
    def __init__(self, name, value = True):
        """By default the bool option is set (value True)"""
        Opt.__init__(self, name, value)

    def __str__(self):
        if not self.setted:
            return ''
        else:
            return self.name
    
    def valid(self, value):
        return value in (True, False)
    
    def choices(self):
        return "True, False"

class ConstOpt(Opt):
    """Constant option, when you just have one possible value
    It optionally takes a regular expression used to check if input is syntactically correct"""
    def __init__(self, name, value = None, regex = None):
        self.regex = regex
        Opt.__init__(self, name, value)
    
    def valid(self, value):
        return (not(self.regex) or re.match(self.regex, value))
    
    def choices(self):
        if not(self.regex):
            return "whatever"
        else:
            return ("must satisfy regex: " + self.regex)
        
class ParamOpt(Opt):
    """Option with a parameter
    This takes a list of possible values and checks every time if input is safe"""
    def __init__(self, name, value, val_list):
        self.val_list = val_list
        Opt.__init__(self, name, value)

    def __iter__(self):
        return iter(self.val_list)

    def valid(self, value):
        return value in self.val_list
    
    def choices(self):
        return "must be in list: " + ', '.join(map(str, self.val_list))