#!/usr/bin/env python
import re
import doctest

# right regular expression in shell (word boundary):
# grep '\<ms\>' result.txt

line = "[  3]  0.0-80.8 sec  1.25 MBytes    130 Kbits/sec  4.121 ms    0/  893 (0%)"
# num with comma
num = re.compile(r"(\d+)(?:\.(\d+))?")

# print line
# print num2.findall(line)

f = num.findall(line)

cells = {
    2 : "time",
    3 : "mb",
    4 : "kbs",
    5 : "ms",
    6 : "miss",
    7 : "rx",
    8 : "cent"
}

def toFlat(tup):
    """tuple to float
    # >>> toFlat((1,10))
    # 1.10
    """
    if tup[1] == '':
        return int(tup[0])
    return round(float(tup[0]) + (float(tup[1]) / 100))
    
def make_dict(line):
    nums = num.findall(line)
    vals = {}
    for c in cells.iterkeys():
        vals[cells[c]] = toFlat(nums[c])
    return vals    

# example file
res = open("result.txt").readlines()
for i in res:
    if re.search(r"\bms\b", i):
        print make_dict(i)





# doing a simple split we get interesting results

if __name__ == '__main__':
    doctest.testmod()