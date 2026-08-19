import time 
import math

class GestureDetector():
    
    def __init__(self):
        self.info_gesture_start:int|None = None

    def set_pixel_landmarks(self, hand:list[list[int,int,int]], pose:list[list[int,int,int]]):
        """ take two lists of landmark pixel coordinates, lile[[index, screen_x, screen_y], [...], ...]
        """
        self.hand_lm = list(hand)
        self.pose_lm = list(pose)

    def find_info_gesture(self):
        thumb_tip = self.hand_lm[4][1:3]
        index_tip = self.hand_lm[8][1:3]
        middle_tip = self.hand_lm[12][1:3]
        ring_tip = self.hand_lm[16][1:3]
        pinky_tip = self.hand_lm[20][1:3]
        index_mcp = self.hand_lm[5][1:3]
        index_dx = abs(index_mcp[0] - index_tip[0])
        index_dy = index_mcp[1] - index_tip[1]
        if index_dy > 3 * index_dx: 
            # index pointing upwerts
            thump_dist = 0
            index_dist = 0
            for tip in [middle_tip, ring_tip, pinky_tip]:
                thump_dist += math.dist(thumb_tip, tip)
                index_dist += math.dist(index_tip, tip)
            if index_dist > 1.6 * thump_dist: 
                # thump colser to the rest of the fingers the index 
                if not self.info_gesture_start:
                    self.info_gesture_start = time.time()
                    return False
                if time.time() - self.info_gesture_start > 1: # hold the gisture 1 sec to be reconised
                    return True
                return False
        # not in the right hand position
        self.info_gesture_start = None
        return False
                
