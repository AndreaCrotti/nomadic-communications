import sys
# Error handling classes
class TestError(Exception):
    def __init__(self, message = ""):
        pass
        # if self.fatal:
        #     sys.exit(self.exitcode)

class FileError(TestError):
    def __init__(self, filename, fatal = False):
        self.exitcode = 1
        self.fatal = fatal
        super(FileError, self).__init__("problem with " + filename)

class NetworkError(TestError):
    def __init__(self, message):
        super(NetworkError, self).__init__(message)

class ConfigurationError(TestError):
    def __init__(self, filename):
        """docstring for __init__"""
        pass

class LibError(TestError):
    def __init__(self, lib, fatal = False):
        self.exitcode = 4
        self.fatal = fatal
        super(LibError, self).__init__("problem with library " + lib)