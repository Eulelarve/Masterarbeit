from collections import defaultdict
from collections import deque
import numpy as np


import math
def f(p):
    p = p[:]
    p[0] = 100
    return p
p = [0,1,2]
t = f(p)
print(p,t)