from collections import defaultdict
from collections import deque
import numpy as np


arr = np.array([[[1],[2]],[[1],[2]],[[3],[4]]])

rgba = np.full((*arr.shape[:2], 4), (0, 0, 255, 50), dtype=np.uint8)

print(rgba.shape)
print(rgba)