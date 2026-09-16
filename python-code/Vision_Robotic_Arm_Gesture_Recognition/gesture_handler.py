import time 
import math
from own_functions import ValueBufferTime

class GestureDetector():
    
    def __init__(self):
        self.hands_lm = []
        self.pose_lm = []
        self.pose_visibilety = []
        self.pose_movement = []
        self.active_hand_id:int|None = None
        self.upper_body_len:int|None = None
        # grab gesture
        self.hand_status:list[int|None] = [None, None]           # 0 is closed, 1 is open, None is no hand
        self.hand_status_before:list[int|None] = [None, None]
        self.grab = [False, False]
        self.releas = [False, False]
        self.is_grabbing = [False, False]

        ## control gestures
        self.pointing_up_start_time:int|None = None
        self.thumb_down_start_time:int|None = None
        self.give_the_finger_start_time:int|None = None
        self.arms_crossed_start_time:int|None = None
        self.covered_eyes_start_time:int|None = None
        self.info_gesture = False
        self.info_trigger = False
        self.termination_gesture = False
        self.visibilety_mode_gesture = False
        self.visibilety_mode_trigger = False
        self.clear_gesture = False
        self.clear_trigger = False
        self.swipe_course:list[dict] = []
        self.hand_to_hand_dist_course = ValueBufferTime(None)
        self.hand_shoulder_x_diff_max:int|None = None
        self.hand_shoulder_x_diff_max_time:int|None = None
        self.swiping_hand_id:int|None = None

    def set_pixel_landmarks(self, hand_left:list[list[int,int,int]],hand_right:list[list[int,int,int]], pose:list[list[int,int,int]]):
        """ take two lists of landmark pixel coordinates, lile[[index, screen_x, screen_y], [...], ...]
        """
        self.hands_lm = hand_left.copy(), hand_right.copy()
        self.pose_lm = pose.copy()

    def find_info_trigger(self):
            self.info_trigger = False # reset trigger
            last_check = self.info_gesture # save results of the last check
            if self.find_info_gesture():
                if last_check == False:
                    # gusture triggered just now  
                    self.info_trigger = True
                    print('gesture detected: info_trigger')
            return self.info_trigger 

    def find_info_gesture(self)->bool:
        self.info_gesture = self.index_pointing_up()
        return self.info_gesture
    
    def index_pointing_up(self)->bool:
        for hand_lm in self.hands_lm:
            if len(hand_lm) == 0:
                # hand not found
                return False
            thumb_tip = hand_lm[4][1:3]
            index_tip = hand_lm[8][1:3]
            middle_tip = hand_lm[12][1:3]
            ring_tip = hand_lm[16][1:3]
            pinky_tip = hand_lm[20][1:3]
            index_mcp = hand_lm[5][1:3]
            # calculate
            index_dx = abs(index_mcp[0] - index_tip[0])
            index_dy = index_mcp[1] - index_tip[1]
            # decisions
            if index_dy > 2 * index_dx: 
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
                    if time.time() - self.pointing_up_start_time > 0.7: 
                        # hold this gesture 0.7 sec
                        return True
                    return False
        # all hand not in the correct position
        self.pointing_up_start_time = None
        return False

    def thumb_down(self)->bool:
        for hand_lm in self.hands_lm:
            if len(hand_lm) == 0:
                # hand not found
                return False
            wrist  = hand_lm[0][1:3]
            thumb_tip = hand_lm[4][1:3]
            index_tip = hand_lm[8][1:3]
            middle_tip = hand_lm[12][1:3]
            ring_tip = hand_lm[16][1:3]
            pinky_tip = hand_lm[20][1:3]
            thumb_mcp = hand_lm[2][1:3]
            index_mcp = hand_lm[5][1:3]
            middle_mcp = hand_lm[9][1:3]
            ring_mcp = hand_lm[13][1:3]
            pinky_mcp = hand_lm[17][1:3]
            shoulder_lift = self.pose_lm[11][1:3]
            shoulder_right = self.pose_lm[12][1:3]
            # claculate
            thumb_dx = abs(thumb_mcp[0] - thumb_tip[0])
            thumb_dy = thumb_tip[1] - thumb_mcp[1]
            palm_dx = abs(index_mcp[0] - pinky_mcp[0])
            palm_dy = abs(index_mcp[1] - pinky_mcp[1])
            # decisions
            thumb_between_shoulders = False
            if shoulder_lift[0] < thumb_tip[0] < shoulder_right[0]:
                thumb_between_shoulders = True
            if shoulder_lift[0] > thumb_tip[0] > shoulder_right[0]:
                thumb_between_shoulders = True
            if thumb_between_shoulders:
                # x position of thumb is between the shoulders
                if palm_dy > palm_dx * 2:
                    # hand is thumb-side down
                    if thumb_dy > thumb_dx: 
                        # thumb pointing down (between 45° and 90°)
                        mcps_dist = 0
                        tips_dist = 0
                        for tip, mcp in [(index_tip, index_mcp),(middle_tip, middle_mcp),(ring_tip, ring_mcp),(pinky_tip, pinky_mcp)]:
                            tips_dist += math.dist(wrist, tip)
                            mcps_dist += math.dist(wrist, mcp)
                        finger_fist = tips_dist < mcps_dist
                        if finger_fist:
                            # finger tips colser to the wrist of the finger mcps
                            if not self.thumb_down_start_time:
                                self.thumb_down_start_time = time.time()
                                return False
                            if time.time() - self.thumb_down_start_time > 1.5: 
                                # hold this gesture 1.5 sec
                                return True
                            return False
        # all hands are not in the correct position
        self.thumb_down_start_time = None
        return False
    
    def give_the_finger(self)->bool:
        for hand_lm in self.hands_lm:
            if len(hand_lm) == 0:
                # hand not found
                return False
            index_tip = hand_lm[8][1:3]
            middle_tip = hand_lm[12][1:3]
            ring_tip = hand_lm[16][1:3]
            pinky_tip = hand_lm[20][1:3]
            middle_mcp = hand_lm[9][1:3]
            middle_dy = middle_mcp[1] - middle_tip[1]
            # middle_dx = abs(middle_mcp[0] - middle_tip[0])
            # if middle_dy > 3 * middle_dx: 
            if middle_dy > 0: 
                # middle finger pointing more upwards
                closer_to_palm = True
                for tip in [index_tip, ring_tip, pinky_tip]:
                    mcp_dist = math.dist(middle_mcp, tip)
                    tip_dist = math.dist(middle_tip, tip)
                    if tip_dist < mcp_dist * 1.0: 
                        closer_to_palm = False
                        break

                if closer_to_palm:
                    # wrist colser to the rest of the fingers the middle finger 
                    if not self.give_the_finger_start_time:
                        self.give_the_finger_start_time = time.time()
                        return False
                    if time.time() - self.give_the_finger_start_time > 2: 
                        # hold this gesture 2 sec
                        return True
                    return False
        # all hands are not in the correct position
        self.give_the_finger_start_time = None
        return False

    def _(self):
        if self.give_the_finger():
            self.feel_slighted()

    def feel_slighted(self):
        self.termination_gesture = True
        print()
        print("     ╭─────────╮")
        print("    ╱           ╲")
        print("   │   ╭╮   ╭╮   │      ╭───────────────────────────────╮")
        print("   │   ╰╯   ╰╯   │      |   down't show me the finger!  |")
        print("   │      ╥      │   ╭──╯   I am out!                   |")
        print("   │    ╭───╮    │  ─╯  ╰───────────────────────────────╯")
        print("   │    ╰───╯    │")
        print("    ╲           ╱")
        print("     ╰─────────╯")
        print("       ╥     ╥")
        print("      ╥       ╥")
                
    def find_grab(self)-> bool|None:
        """ set and returns if the hand is grabbing or releasing now
            returns:
                True -> grab
                False -> releas
                None -> no action
        """
        grab = []
        for i in range(len(self.hand_status)):
            self.grab[i] = False
            self.releas[i] = False
            if self.hand_status_before[i] == 1 and self.hand_status[i] == 0:
                self.grab[i] = True
                self.is_grabbing[i] = True
                grab.append(True)
            elif self.is_grabbing[i] and self.hand_status[i] == 1:
                self.releas[i] = True
                self.is_grabbing[i] = False
                grab.append(True)
            else:
                grab.append(None)
            self.hand_status_before[i] = self.hand_status[i]
        return grab

    def find_termination_gesture(self)->bool:
        self.termination_gesture = self.arms_crossed() 
        self._()
        if self.termination_gesture:
            print('gesture detected: termination')
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
                print('gesture detected: visibilety_mode_trigger')
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
    
    def double_arm_swipe(self)->bool:
        gesture_max_time = 0.7
        self.hand_to_hand_dist_course.buffering_time = gesture_max_time
        x_hand_l = self.pose_lm[15][1]
        x_hand_r = self.pose_lm[16][1]
        distance = x_hand_l - x_hand_r
        self.hand_to_hand_dist_course.add(distance)
        if self.hand_to_hand_dist_course.difference > self.upper_body_len * 2:
            print('dist')#test
            # swipe distanze is large enough
            min_dist = self.hand_to_hand_dist_course.min
            max_dist = self.hand_to_hand_dist_course.max
            if min_dist < -self.upper_body_len * 0.7 and  max_dist > self.upper_body_len * 0.7:
                # arms are crossing during swiping
                print('dist_x')#test
                print(min_dist,max_dist)#test
                return True
        # hand moves not fare or fast enough
        return False

    def find_clear_gesture(self)->bool:
        self.clear_gesture = self.thumb_down()
        if self.clear_gesture:
            print('gesture detected: clear')
        return self.clear_gesture

    def find_clear_trigger(self)->bool:
        self.clear_trigger = False # reset trigger
        last_check = self.clear_gesture # save results of the last find gesture check
        if self.find_clear_gesture():
            if last_check == False:
                # gusture triggered just now  
                self.clear_trigger = True
                print('gesture detected: clear_gesture')
        return self.clear_trigger 






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
