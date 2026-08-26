import numpy as np
from Vision_Robotic_Arm_Gesture_Recognition.own_functions import ValueBuffer, close_to, median
from collections import deque, defaultdict

import math

t= defaultdict(lambda: ValueBuffer(6))
t['w'].add(4)
t['w'].add(4)
t['w'].add(4)
t['e'].add(5)
t['e'].add(5)
t['e'].add(5)
print(t['e'].average, t['w'].average)

