import sys, os

def clear():
    """Clear the terminal screen, it should be portable in this way"""
    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')