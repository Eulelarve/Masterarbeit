import time 
import math
from own_functions import ValueBufferTime

class GestureDetector():
    
    def __init__(self):
        self.hand_lm = []
        self.pose_lm = []
        self.pose_visibilety = []
        self.pose_movement = []
        self.active_hand_id:int|None = None
        self.upper_body_len:int|None = None
        # grap gesture
        self.hand_status:bool|None = None           # 0 is closed, 1 is open, None is no hand
        self.hand_status_before:bool|None = None
        self.grab = False
        self.releas = False
        self.is_grabbing = False

        ## control gestures
        self.pointing_up_start_time:int|None = None
        self.give_the_finger_start_time:int|None = None
        self.arms_crossed_start_time:int|None = None
        self.covered_eyes_start_time:int|None = None
        self.info_gesture = False
        self.termination_gesture = False
        self.visibilety_mode_gesture = False
        self.visibilety_mode_trigger = False
        self.clear_gesture = False
        self.swipe_course:list[dict] = []
        self.hand_shoulder_x_diff_max:int|None = None
        self.hand_shoulder_x_diff_max_time:int|None = None
        self.swiping_hand_id:int|None = None

    def set_pixel_landmarks(self, hand:list[list[int,int,int]], pose:list[list[int,int,int]]):
        """ take two lists of landmark pixel coordinates, lile[[index, screen_x, screen_y], [...], ...]
        """
        self.hand_lm = list(hand)
        self.pose_lm = list(pose)

    def find_info_gesture(self)->bool:
        self.info_gesture = self.index_pointing_up()
        return self.info_gesture
    
    def index_pointing_up(self)->bool:
        thumb_tip = self.hand_lm[4][1:3]
        index_tip = self.hand_lm[8][1:3]
        middle_tip = self.hand_lm[12][1:3]
        ring_tip = self.hand_lm[16][1:3]
        pinky_tip = self.hand_lm[20][1:3]
        index_mcp = self.hand_lm[5][1:3]
        index_dx = abs(index_mcp[0] - index_tip[0])
        index_dy = index_mcp[1] - index_tip[1]
        if index_dy > 3 * index_dx: 
            # index pointing upwards
            closer_to_thumb = True
            for tip in [middle_tip, ring_tip, pinky_tip]:
                thump_dist = math.dist(thumb_tip, tip)
                index_dist = math.dist(index_tip, tip)
                if index_dist < 1.6 * thump_dist: 
                    closer_to_thumb = False
                    break

            if closer_to_thumb:
                # thump colser to the rest of the fingers the index 
                if not self.pointing_up_start_time:
                    self.pointing_up_start_time = time.time()
                    return False
                if time.time() - self.pointing_up_start_time > 1: 
                    # hold this gesture 1 sec
                    return True
                return False
        # hand not in the correct position
        self.pointing_up_start_time = None
        return False
    
    def give_the_finger(self)->bool:
        index_tip = self.hand_lm[8][1:3]
        middle_tip = self.hand_lm[12][1:3]
        ring_tip = self.hand_lm[16][1:3]
        pinky_tip = self.hand_lm[20][1:3]
        middle_mcp = self.hand_lm[9][1:3]
        middle_dy = middle_mcp[1] - middle_tip[1]
        # middle_dx = abs(middle_mcp[0] - middle_tip[0])
        # if middle_dy > 3 * middle_dx: 
        if middle_dy > 0: 
            # middle finger pointing more upwards
            closer_to_wrist = True
            for tip in [index_tip, ring_tip, pinky_tip]:
                wrist_dist = math.dist(middle_mcp, tip)
                middle_dist = math.dist(middle_tip, tip)
                if middle_dist < 1.0 * wrist_dist: 
                    closer_to_wrist = False
                    break

            if closer_to_wrist:
                # wrist colser to the rest of the fingers the middle finger 
                if not self.give_the_finger_start_time:
                    self.give_the_finger_start_time = time.time()
                    return False
                if time.time() - self.give_the_finger_start_time > 2: 
                    # hold this gesture 2 sec
                    return True
                return False
        # hand not in the correct position
        self.give_the_finger_start_time = None
        return False

    def _(self):
        if self.give_the_finger():
            self.feel_slighted()

    def feel_slighted(self):
        print('f**k you self!\nI am out!')
        self.termination_gesture = True
                
    def find_grap(self)-> bool|None:
        """ set and returns if the hand is grabbing or releasing now
            returns:
                True -> grab
                False -> releas
                None -> no action
        """
        self.grab = False
        self.releas = False

        if self.hand_status_before == 1 and self.hand_status == 0:
            self.grab = True
            self.is_grabbing = True
            return True
        elif self.is_grabbing and self.hand_status == 1:
            self.releas = True
            self.is_grabbing = False
            return False
        return None

    def find_termination_gesture(self)->bool:
        self.termination_gesture = self.arms_crossed() 
        self._()
        return self.termination_gesture



    def arms_crossed(self)->bool:
        hand_left = self.pose_lm[19][1:3]
        hand_right = self.pose_lm[20][1:3]
        elbow_left = self.pose_lm[13][1:3]
        elbow_right = self.pose_lm[14][1:3]
        forearm_len = math.dist(hand_left, elbow_left)
        if hand_left[1] + forearm_len/3 < elbow_right[1]:
            if hand_right[1] + forearm_len/3 < elbow_left[1]:
                # both hands above both elbows
                x_direction_hands = hand_left[0] < hand_right[0]
                x_direction_elbows = elbow_left[0] < elbow_right[0]
                if x_direction_elbows != x_direction_hands:
                    # arms crossed
                    if not self.arms_crossed_start_time:
                        self.arms_crossed_start_time = time.time()
                        return False
                    if time.time() - self.arms_crossed_start_time > 2: 
                        # hold this gesture 2 sec
                        return True
                    return False
        # arms not in the correct position
        self.arms_crossed_start_time = None
        return False

    def hands_covering_eyes(self)->bool:
        hl=17; hr=18
        hand_left = self.pose_lm[hl][1:3]
        hand_right = self.pose_lm[hr][1:3]
        eye_left = self.pose_lm[3][1:3]
        eye_right = self.pose_lm[6][1:3]
        eyes_dist = math.dist(eye_left, eye_right)
        hand_eye_dist_left = math.dist(hand_left, eye_left)
        hand_eye_dist_right = math.dist(hand_right, eye_right)
        if hand_eye_dist_left < eyes_dist * 1.4 > hand_eye_dist_right:
            # hands are close to the eyes
            if self.pose_visibilety[hl][1] and self.pose_visibilety[hr][1]:
                # hands are visible
                # if not self.pose_movement[hl][1] and not self.pose_movement[hr][1]:
                #     # hands ar not moving
                    if not self.covered_eyes_start_time:
                        self.covered_eyes_start_time = time.time()
                        return False
                    if time.time() - self.covered_eyes_start_time > 0.5: 
                        # hold this gesture for 0.5 sec
                        return True
                    return False
        # arms not in the correct position
        self.covered_eyes_start_time = None
        return False

    def find_visibilety_mode_gesture(self):
        self.visibilety_mode_gesture = self.hands_covering_eyes()
        return self.visibilety_mode_gesture

    def find_visibilety_mode_trigger(self):
        self.visibilety_mode_trigger = False # reset trigger
        last_check = self.visibilety_mode_gesture # save results of the last check
        if self.find_visibilety_mode_gesture():
            if last_check == False:
                # gusture triggered just now  
                self.visibilety_mode_trigger = True
        return self.visibilety_mode_trigger          

    def arm_swipe(self)->bool:
        if self.active_hand_id != self.swiping_hand_id:
            # active hand changed
            self.swipe_course.clear()
            self.swiping_hand_id = self.active_hand_id

        hand = self.pose_lm[self.swiping_hand_id][1:3]
        time_now = time.time()
        self.swipe_course.append({
                                    'time':time_now, 
                                    'x': hand[0], 
                                    'y':hand[1]
                                })
        while time_now - self.swipe_course[0]['time'] > 0.7:
            # while the first element is older then 0.7 sec
            self.swipe_course.pop(0)

        x_max = max(e['x'] for e in self.swipe_course)
        x_min = min(e['x'] for e in self.swipe_course)
        if x_max - x_min > self.upper_body_len * 2:
            # hand travels in x direction more than the upper body size times 2
            y_max = max(e['y'] for e in self.swipe_course)
            y_min = min(e['y'] for e in self.swipe_course)
            if y_max - y_min < self.upper_body_len * 0.5:
                # hand travels in x direction less than the upper body size times 0.5
                self.swipe_course.clear()
                return True
        # hand moves not fare or fast enough
        return False

    def find_clear_gesture(self)->bool:
        self.clear_gesture = self.arm_swipe()
        return self.clear_gesture







        if self.hand_shoulder_x_diff_max is None:
            # no refference jet, so set one
            self.hand_shoulder_x_diff_max = hand_shoulder_x_diff_now
            return False
        
        direction_1 = self.hand_shoulder_x_diff_max > 0
        direction_2 = hand_shoulder_x_diff_now > 0
        if direction_1 == direction_2:
            # hand is still on the same side from the shoulder
            if abs(self.hand_shoulder_x_diff_max) < abs(hand_shoulder_x_diff_now):
                # new max distance
                self.hand_shoulder_x_diff_max = hand_shoulder_x_diff_now
        else:
            # hand is on the other side from the shoulder
            swip_distance = self.hand_shoulder_x_diff_max - hand_shoulder_x_diff_now
            if abs(swip_distance) > self.upper_body_len * 1.5:
                return True
