import numpy as np
from Vision_Robotic_Arm_Gesture_Recognition.own_functions import ValueBuffer

def moving_average(data, window=5):
    kernel = np.ones(window) / window
    return np.convolve(data, kernel, mode="same")

# Testsignal
signal = np.array([
    0, 0, 0, 0, 0,
    10, 10, 10, 10, 10,
    10, 10, 10, 10, 10,
    10, 10, 10, 10, 10
], dtype=float)

b1 = ValueBuffer(5)
b2 = ValueBuffer(5)
for i in signal:
    e = b1.add_and_get_average(i)
    r = b2.add_and_get_average(e)
    print(i,e,r)
