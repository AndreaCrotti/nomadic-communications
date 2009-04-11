from distutils.core import setup

setup(
    name = "nomadic communications",
    version = "0.2",
    author = "Andrea Crotti",
    description = "set of python scripts to automatize testing and network performaces performances",
    author_email = "andrea.crotti@studenti.unitn.it",
    url = "http://github.com/AndreaCrotti/nomadic-communications/",
    py_modules = ['parse_iperf', 'test/test', 'tester', 'analysis/analyze'],
    license = "gpl",
    # TODO adding classifiers to create the egg and put it on pypi
)