"""
    this code bassed on code from another project.
    Projectlink: https://github.com/e-candeloro/Vision-Robotic-Arm-Gesture-Recognition/tree/master 
"""

import mediapipe as mp
import numpy as np
import cv2

import time
import math

import settings as S

from own_functions import fit_roi_landmarks_to_frame, ValueBuffer, close_to, ListBuffer, ValueBufferTime, MoveDetector
from coordinates_handler import get_center_of_landmarks, mediapipe_world_to_room
from angle_handler import angle_between_points, draw_angle_between_points
from collections import defaultdict


POSE_CONNECTIONS = [
    # Gesicht
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),

    # Oberkörper
    (11, 12),
    (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21),
    (17, 19),
    (12, 14), (14, 16),
    (16, 18), (16, 20), (16, 22),
    (18, 20),

    # Rumpf
    (11, 23), (12, 24),
    (23, 24),

    # Linkes Bein
    (23, 25), (25, 27),
    (27, 29), (29, 31),
    (27, 31),

    # Rechtes Bein
    (24, 26), (26, 28),
    (28, 30), (30, 32),
    (28, 32),
]

class PoseDetector():
    def __init__(self, mode=False, modCompl=1, upBody=False, smooth=True, segm=False, smooth_seg=True, detCon=0.5, trackCon=0.5):
        """Pose detector class that is used to detect the position of the body keypoints.

        Args:
            mode (bool, optional): If set to True, enables static image mode. Defaults to False.
            
            modCompl (int, optional): Complexity of the pose landmark model: 0, 1 or 2. Landmark accuracy as well as inference latency generally go up with the model complexity. Default to 1.
            
            upBody (bool, optional): If set to True, set detection for frames containing only upper body . Defaults to False.
            
            smooth (bool, optional):If set to true, the solution filters pose landmarks across different input images to reduce jitter, but ignored if mode is also set to true. Default to true.
            
            segm (bool, optional):If set to true, in addition to the pose landmarks the solution also generates the segmentation mask. Default to false.
            
            smooth_seg (bool, optional): If set to true, the solution filters segmentation masks across different input images to reduce jitter. Ignored if enable_segmentation is false or static_image_mode is true. Default to true.
            
            detCon (float, optional): Minimum confidence value ([0.0, 1.0]) from the person-detection model for the detection to be considered successful. Default to 0.5
            
            trackCon (float, optional): Minimum confidence value ([0.0, 1.0]) from the landmark-tracking model for the pose landmarks to be considered tracked successfully, or otherwise person detection will be invoked automatically on the next input image. Setting it to a higher value can increase robustness of the solution, at the expense of a higher latency. Ignored if static_image_mode is true, where person detection simply runs on every image. Default to 0.5.
        """
        self.lm_range = range(33)
        self.mode = mode  # static image mode
        self.modCompl = modCompl
        self.upBody = upBody
        self.smooth = smooth
        self.segm = segm
        self.smooth_seg = smooth_seg
        self.detCon = detCon  # detection confidence threshold
        self.trackCon = trackCon  # tracking confidence threshold
        self.hand_moving_buffer = ValueBuffer(5)
        self.hand_side:list[str|None] = [None,None]

        self.mpPose = mp.solutions.pose
        self.pose = self.mpPose.Pose(static_image_mode=self.mode,
                                     model_complexity=self.modCompl,
                                     smooth_landmarks=self.smooth,
                                     enable_segmentation=self.segm,
                                     smooth_segmentation=self.smooth_seg,
                                     min_detection_confidence=self.detCon,
                                     min_tracking_confidence=self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils
        self.move_detectors = [MoveDetector(S.moving_min_speed, S.moving_check_time) for _ in self.lm_range]
        self.left_hand_points = S.left_hand_landmark_ids
        self.right_hand_points = S.right_hand_landmark_ids
        self._left = 'left'
        self._right = 'right'


    def create_moving_list(self):
        if not self.lm_list:
            return []
        self.lm_movment_list = []
        for (i,x,y) in self.lm_list:
            speed = self.move_detectors[i].is_moving((x,y))
            self.lm_movment_list.append([i, speed])

        return self.lm_movment_list

    def findPose(self, frame, ):
        """
        Detects the pose of the person in the given image.

        Args:
            frame (OpenCV BGR frame): img (opencv image in BGR)
            draw (bool, optional): draw the keypoint if set to true. Defaults to True.

        Returns:
            opencv image in BGR with keypoints drawn if draw is set to true
        """
        
        imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(imgRGB)
        self.frame_w = frame.shape[1]
        self.frame_h = frame.shape[0]

        # if self.results.pose_landmarks:
        #     if draw:
        #         self.mpDraw.draw_landmarks(
        #             frame_to_draw, self.results.pose_landmarks, self.mpPose.POSE_CONNECTIONS)
        # return frame

    def create_pixel_landmark_list(self)->list:
       
        self.lm_list = []

        if self.results.pose_landmarks:
            pose = self.results.pose_landmarks
            for id, lm in enumerate(pose.landmark):
                x, y = (lm.x * self.frame_w), (lm.y * self.frame_h)
                self.lm_list.append([id, int(x), int(y)])

        return self.lm_list

    def draw_skeleton(self, frame):
        connections = POSE_CONNECTIONS
        for start, end in connections:
            cv2.line(
                frame,
                self.lm_list[start][1:3],
                self.lm_list[end][1:3],
                S.white,
                2
            )
        for id, *xy in self.lm_list:
            cv2.circle(frame, xy, 5, S.white, -1)

    def create_visibility_list(self)->list:
        self.lm_visibility = []
        if self.results.pose_landmarks:
            pose = self.results.pose_landmarks
            for id, lm in enumerate(pose.landmark):
                if self.landmarke_in_frame(id):
                    vis = lm.visibility
                else:
                    vis = 0
                self.lm_visibility.append([id, vis])
        return self.lm_visibility

    def landmarke_in_frame(self, id:int)->bool:
        x,y = self.lm_list[id][1:3]
        if 0 <= x < self.frame_w and 0 <= y < self.frame_h:
            return True
        return False

    def find_specific_points(self,mode:str, keep_hand_side:bool=False, mirrowed:bool=False):
        landmarks = self.lm_list
        if keep_hand_side:
            if mode.lower() == 'both':
                vh = self.get_visible_hand_side()
                if None not in vh: 
                    # in both hand mode, it still cann add a hand if it get visible
                    self.hand_side = vh
        else:
            # choose the hand side 
            self.hand_side = self.get_hand_side(mode, mirrowed)

        self.shoulder = [None, None]    
        self.hip = [None, None]  
        self.hand_center = [None, None] 

        if self._left in self.hand_side: # left hand
            center = get_center_of_landmarks(landmarks,self.left_hand_points[1:3]) # just take 17, 19 to get the left hand center
            center.insert(0, self.left_hand_points[2]) # [hand_point_index , x, y]  while idex = 19
            self.hand_center[0] = center
            self.shoulder[0] = landmarks[11] # left shoulder
            self.hip[0] = landmarks[23]
        if self._right in self.hand_side: # right hand
            center = get_center_of_landmarks(landmarks,self.right_hand_points[1:3]) # just take 18, 20 to get the right hand center
            center.insert(0, self.right_hand_points[2]) # [hand_point_index , x, y]  while index = 20
            self.hand_center[1] = center
            self.shoulder[1] = landmarks[12] # right shoulder
            self.hip[1] = landmarks[24]

    
    def calibrate_arm_length(self,time_to_calibrate=2.0, max_rel_hight_diff=1/4):
        left_hand_center = get_center_of_landmarks(self.lm_list,[17,19])
        right_hand_center = get_center_of_landmarks(self.lm_list,[18,20])
        left_shoulder = self.lm_list[11][1:]
        right_shoulder = self.lm_list[12][1:]
        left_hip = self.lm_list[23][1:]
        
        max_y_pixel_diff = (left_hip[1] - left_shoulder[1]) * max_rel_hight_diff
        if close_to(max_y_pixel_diff, right_shoulder,
                    left_hand_center,right_hand_center,left_shoulder):
            
            if self.calibranion_start_time > time_to_calibrate:
                left_arm = math.dist(left_hand_center,left_shoulder)
                right_arm = math.dist(right_hand_center,right_shoulder)
                self.arm_len = (left_arm + right_arm)/2

        else:
            self.calibranion_start_time = time.perf_counter()


    def create_world_landmark_list(self):
        '''
        Given and image, returns the 3D pose keypoints position in the format of a list of lists
        [[id_point0, x_point0, y_point0, zpoint0], ...]
        The keypoints are in world coordinates and in meter, with the origin in the middle point of the hips
        If additional info is True, returns a list of list in the format
        [[id_point0, x_point0, y_point0, zpoint0, visibility], ...]

        Keypoints list  are shown on this site: https://google.github.io/mediapipe/images/mobile/pose_tracking_full_body_landmarks.png

        :param: additional_info (returns visibility in the keypoint list. Default is False)
        :draw: bool (draws a matplotlib 3d graph of all the keypoints in world coordinates. Default is False)

        :returns: 
            lm_3dlist (list of lists of keypoints)
        '''
        self.lm_3dlist = []

        if self.results.pose_landmarks:
            pose = self.results.pose_world_landmarks
            for id, lm in enumerate(pose.landmark):
                self.lm_3dlist.append([id, lm.x, lm.y, lm.z])
        return self.lm_3dlist

    def estimate_room_coordinates(self):
        self.create_world_landmark_list()
        self.room_lm_list = mediapipe_world_to_room(self.lm_3dlist)
        return self.room_lm_list

    def findAngle(self, frame, i1: int, i2: int, i3: int, angle3d=False, draw=True,text_pos=(-50,+50)):
        '''Find the angle between 3 points i1, i2, i3 in succession, where i2 is the point where the angle is measured.
        For the points, only the index number is required. Please refer to this image to select the appriopriate keypoints: https://google.github.io/mediapipe/images/mobile/pose_tracking_full_body_landmarks.png

        Example: elbow angle, given the shoulder keypoint, the elbow keypoint and the wrist keypoint

        :param: frame (opencv frame)
        :i1:first point index
        :i2:second point index
        :i3:third point index
        :angle3d: Bool: performs 3d angle computation, default is False
        :flip_2dangle: Bool: flips the angle computation if it is in 2d, default is False
        :draw: Bool (optional): draws additional info, default is True

        Returns:
            -angle: angle in degrees between the segment s12 and the segment s23 having p2 as vertex, where the angle is located
        '''

        if angle3d:
            assert len(
            self.lm_3dlist) > 0, f"3D Landmark list is empty, use this function only after using the FindPose and Find3DPosePosition methods"

            p1 = self.lm_3dlist[i1][1:4]
            p2 = self.lm_3dlist[i2][1:4]
            p3 = self.lm_3dlist[i3][1:4]


        else:
            assert len(
            self.lm_list) > 0, f"Landmark list is empty, use this function only after using the FindPose and FindPosePosition methods"

            p1 = self.lm_list[i1][1:3]
            p2 = self.lm_list[i2][1:3]
            p3 = self.lm_list[i3][1:3]

        angle = angle_between_points(p1,p2,p3)

        if draw:
            # draw the angle and the keypoints, and the connections between them.
            p1 = self.lm_list[i1][1:3]
            p2 = self.lm_list[i2][1:3]
            p3 = self.lm_list[i3][1:3]
            draw_angle_between_points(frame,angle,p1,p2,p3,text_pos)

        return angle

    # added funktios

    def draw_landmarks(self, frame, landmark_ids:tuple[int], 
                       conection_list:tuple[tuple[int, int]]=None, 
                       color_landmarks:tuple[int, int, int]=(0,255,0), 
                       color_connections:tuple[int, int, int]=(255, 0, 0), 
                       thickness_landmarks:int=3, 
                       thickness_connections:int=2):
        '''
        Draws the landmarks and the connections between them on the given frame.
            Args:
                frame (opencv BGR image): the image on which the landmarks and connections will be drawn
                landmarks (tuple of int): a tuple containing the index of the landmarks to be drawn. The index of the landmarks can be found in this image: https://google.github.io/mediapipe/images/mobile/pose_tracking_full_body_landmarks.png
                conection_list (tuple of tuple of int, optional): a tuple containing the connections to be drawn. Each connection is represented as a tuple of two integers, where each integer is the index of a landmark. The index of the landmarks can be found in this image: https://google.github.io/mediapipe/images/mobile/pose_tracking_full_body_landmarks.png. Defaults to None, which means that no connections will be drawn.
                color_landmarks (tuple of int, optional): a tuple containing the BGR color values for the landmarks. Defaults to (0, 255, 0), which is green.
                color_connections (tuple of int, optional): a tuple containing the BGR color values for the connections. Defaults to (255, 0, 0), which is blue.
                thickness_landmarks (int, optional): the thickness of the landmarks. Defaults to 3.
                thickness_connections (int, optional): the thickness of the connections. Defaults to 2.
        '''

        for idx in landmark_ids:

            lm = self.results.pose_landmarks.landmark[idx]

            x = int(lm.x * frame.shape[1])
            y = int(lm.y * frame.shape[0])

            cv2.circle(frame, (x, y), thickness_landmarks, color_landmarks, cv2.FILLED)
        
        if conection_list:
            for p0, p1 in conection_list:

                cv2.line(
                    frame,
                    p0,
                    p1,
                    color_connections,
                    thickness_connections
                )

    def get_upper_points(self,points_list:list[list]):
        pose_landmarks = self.lm_list
        y_min_pos = float('inf')
        for points in points_list:
            y_sum = sum([pose_landmarks[p][2] for p in points])
            if y_sum < y_min_pos:
                y_min_pos = y_sum
                most_top_points = points
        return most_top_points

    def get_visible_hand_side(self)->list:
        none = [None, None]
        left = [self._left, None]
        right = [None, self._right]
        both = [self._left, self._right]
        v15 = self.lm_visibility[15][1] # left hand wrist in screen
        v16 = self.lm_visibility[16][1] # right hand wrist in screen

        # if both hands are out of the screen borders
        if v15 == v16 == 0:
            return none
        # if only one hand is visivle in screen return this one
        if v15 < S.visibility_threshold or v16 < S.visibility_threshold:
            if  v15 > v16:
                return left
            else:
                return right
        return both

    def get_hand_side(self, choose:str='both', mirrored:bool=False):
        """ choose between left, right or top hand based on the pose landmarks
        Args:
            choose: 'left', 'right', 'top', 'moving', 'both'
            mirrored: if the image is mirrored, left and right are switched
        Returns:
            hand_center: index of the chosen wrist landmark (15 for left, 16 for right)
        
        """
        left = [self._left, None]
        right = [None, self._right]
        both = [self._left, self._right]
        lm_left = self.left_hand_points
        lm_right = self.right_hand_points
        # only the first leter is capital letter, so it is uniform for all spelling options
        choose = choose.lower() 

        # if only one hand is in screen return this one
        vh = self.get_visible_hand_side()
        if None in vh:
            return vh
            
        elif choose == 'both':
            return both

        elif choose == "top":
            top_hand = self.get_upper_points([lm_left, lm_right])
            if top_hand == lm_left:
                return left
            return right

        elif choose == "left":
            return left if not mirrored else right

        elif choose == "right":
            return right if not mirrored else left

        elif choose in ['moving','move','fastest']:
            fhp = self.get_fastest_hand_point()
            if fhp:
                speed = self.lm_movment_list[fhp][1]
                if speed >= S.hand_change_min_speed:
                    if fhp in self.left_hand_points:
                        return left
                    elif fhp in self.right_hand_points:
                        return right
        else:
            print(f"Invalid hand selection mode: {choose}. Please choose 'top', 'left', 'right' or 'moving'.")


    def get_fastest_point(self, point_ids:list=None):
        if point_ids is None:
            point_ids = self.lm_range
        max_speed = 0
        fastest_id = None
        for id in point_ids:
            speed = self.lm_movment_list[id][1]
            if speed > max_speed:
                max_speed = speed
                fastest_id = id
        return fastest_id

    def get_fastest_hand_point(self)->str:
        hand_ids = [*self.left_hand_points, *self.right_hand_points]
        fastest = self.get_fastest_point(hand_ids)
        return fastest

    def get_upper_body_length(self):
        if self.lm_list:
            marks = self.lm_list
        elif self.lm_3dlist:
            marks = self.lm_3dlist
        else:
            raise Exception('Landmark list is empty, use this function only after using the FindPose and FindPosePosition methods')
        x_y_shoulder = (np.array(marks[12][1:3]) + marks[13][1:3]) / 2 # midle between ledt and right sholder side
        x_y_hip = (np.array(marks[24][1:3]) + marks[23][1:3]) / 2 

        # compute upper body lenght as L2 norm between the upper palm midpoint and lower palm midpoint
        body_len = np.linalg.norm(x_y_shoulder - x_y_hip, ord=2)
        return body_len


# ===================================================
# Hands
# ===================================================

HAND_CONNECTIONS = [
    # Daumen
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),

    # Zeigefinger
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),

    # Mittelfinger
    (0, 9),
    (9, 10),
    (10, 11),
    (11, 12),

    # Ringfinger
    (0, 13),
    (13, 14),
    (14, 15),
    (15, 16),

    # Kleiner Finger
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),
]

class HandDetector():
    def __init__(self, mode=False, maxHands=1, modCompl=1, detCon=0.5, trackCon=0.5):
        """Hand detector class that is used to detect the hand keypoints.

        Args:
            mode (bool, optional): If set to false, the solution treats the input images as a video stream. It will try to detect hands in the first input images, and upon a successful detection further localizes the hand landmarks. In subsequent images, once all max_num_hands hands are detected and the corresponding hand landmarks are localized, it simply tracks those landmarks without invoking another detection until it loses track of any of the hands. This reduces latency and is ideal for processing video frames. If set to true, hand detection runs on every input image, ideal for processing a batch of static, possibly unrelated, images. Default to false.
            
            maxHands (int, optional): Maximum number of hands to detect. Default to 1.
            
            modCompl (int, optional): Complexity of the hand landmark model: 0 or 1. Landmark accuracy as well as inference latency generally go up with the model complexity. Default to 1.
            
            detCon (float, optional): Minimum confidence value ([0.0, 1.0]) from the hand detection model for the detection to be considered successful. Default to 0.5.
            
            trackCon (float, optional): Minimum confidence value ([0.0, 1.0]) from the landmark-tracking model for the hand landmarks to be considered tracked successfully, or otherwise hand detection will be invoked automatically on the next input image. Setting it to a higher value can increase robustness of the solution, at the expense of a higher latency. Ignored if static_image_mode is true, where hand detection simply runs on every image. Default to 0.5.
        """
        self.lm_range = range(21)
        self.mode = mode  # static image mode,
        self.maxHands = maxHands  # max number of hands to track
        self.modCompl = modCompl  # complexity of the model (can be 0 or 1)
        self.detCon = detCon  # detection confidence threshold
        self.trackCon = trackCon  # tracking confidence threshold
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(static_image_mode=self.mode,
                                        max_num_hands=self.maxHands,
                                        model_complexity=self.modCompl,
                                        min_detection_confidence=self.detCon,
                                        min_tracking_confidence=self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils

        self.is_hand_open:int = None
        self.no_hand_counter = 0

    ### added methods
    def get_hand_centers(self, frame=None):
        used_marks = [5,17]
        if self.results.multi_hand_landmarks:
            hands_center = []
            for hand_landmarks in self.results.multi_hand_landmarks:
                x_coords = [hand_landmarks.landmark[i].x for i in used_marks]
                y_coords = [hand_landmarks.landmark[i].y for i in used_marks]
                center_x = sum(x_coords) / len(x_coords)
                center_y = sum(y_coords) / len(y_coords)
                if frame is not None:
                    center_x *= frame.shape[1]
                    center_y *= frame.shape[0]
                    
                hands_center.append((center_x, center_y))

            return hands_center
        
    def hand_close_to(self, should_pos:list, max_distance, frame, hand_side_index:int=0, draw=False):
        hs_i = hand_side_index
        # first chesk
        hand_centers = self.get_hand_centers()
        if not hand_centers:
            return False
        # check parameters
        should_pos = list(should_pos) # make sure it is a list, not a tuple and make a copy of it, so the original list is not changed
        if max_distance >= 1: # max distance is bigger than 1, so it is in pixel values, change to relative values
            max_distance = max_distance / frame.shape[0] # use height of the frame for relative distance
        if should_pos[0] >= 1: # x coordinate is bigger than 1, so it is in pixel values, change to relative values
            should_pos[0] = should_pos[0] / frame.shape[1]
        if should_pos[1] >= 1: # y coordinate is bigger than 1, so it is in pixel values, change to relative values
            should_pos[1] = should_pos[1] / frame.shape[0]
        # claculate distance x y
        x_diff = abs(hand_centers[hs_i][0] - should_pos[0])
        y_diff = abs(hand_centers[hs_i][1] - should_pos[1])
        # elliptical rectification
        x_diff = x_diff / frame.shape[1] * frame.shape[0] # x dist = x dist / x frame * y frame
        # check distance
        if x_diff**2 + y_diff**2 <= max_distance**2:
            color = S.green
            output = True
        else:
            color = S.red
            output = False
        # draw
        if draw:
            radius = int(max_distance * frame.shape[0]) # change to pixel values
            cv2.circle(frame, (int(should_pos[0]*frame.shape[1]), int(should_pos[1]*frame.shape[0])), radius, color, 1) # circle
            cv2.circle(frame, (int(hand_centers[hs_i][0]*frame.shape[1]), int(hand_centers[hs_i][1]*frame.shape[0])), 3, S.red, -1) # dot
        return output
      
       

    def choose_hand(self, left_right_top='top'):
        """ Chooses the hand landmarks and index to return based on the specified mode.
        Args:
            left_right_top (str, optional): Mode for selecting hand landmarks. 
                "top" - selects the hand whose center is highest in the image.
                "left" - selects the homans left hand.
                "right" - selects the homans right hand.
                "first" - selects the first detected hand.
                Default is "top".
        Returns:
            hand_landmarks: The selected hand landmarks or None if no hand is detected.
            index: The index of the selected hand in the multi_hand_landmarks list, or None if no hand is detected.
        """
        self.hand_landmarks = None
        index:int = None

        if self.results.multi_hand_landmarks and self.results.multi_handedness:
            
            # only the first leter is capital letter, so if fits to the Mediapipe label format
            left_right_top = left_right_top.capitalize() 


            #--------------------------------------------------
            # Only one hand detected, return it regardless of the mode
            #--------------------------------------------------

            if len(self.results.multi_hand_landmarks) == 1 or left_right_top == "First":
                index = 0
            
            # --------------------------------------------------
            # Oberste Hand
            # --------------------------------------------------

            elif left_right_top == "Top":

                top_hand, index = self._get_topmost_hand(
                    self.results.multi_hand_landmarks
                )

            # --------------------------------------------------
            # Linke oder rechte Hand
            # --------------------------------------------------

            elif left_right_top in ("Left", "Right"):

                desired_label = left_right_top.capitalize()

                for i, (hand_landmarks, handedness) in enumerate(zip(
                    self.results.multi_hand_landmarks,
                    self.results.multi_handedness)):

                    label = handedness.classification[0].label

                    if label == desired_label:
                        index = i

            elif left_right_top == 'both':
                pass
            else:
            # --------------------------------------------------
            # Invalid mode
            # --------------------------------------------------

                print(f"Invalid hand selection mode: {left_right_top}. Please choose 'top', 'left' or 'right'.")

        if index is not None:
            self.hand_landmarks = self.results.multi_hand_landmarks[index].landmark
            self.hand_world_landmarks = self.results.multi_hand_world_landmarks[index].landmark

        return index 


    def _get_topmost_hand(self, multi_hand_landmarks):
        """
        Gibt die Hand zurück, deren Mittelpunkt
        am weitesten oben im Bild liegt.
        """

        top_hand_landmarks = None
        best_y = float("inf")
        index = None

        for i, hand_landmarks in enumerate(multi_hand_landmarks):

            mean_y = sum(
                lm.y for lm in hand_landmarks.landmark
            ) / len(hand_landmarks.landmark)

            if mean_y < best_y:
                best_y = mean_y
                top_hand_landmarks = hand_landmarks
                index = i

        return top_hand_landmarks, index

    def findHands(self,frame, roi=None, frame_to_draw=None, draw_roi=True):
        """ Detects the hands in the input image.

        Args:
            frame (OpenCV BGR image): Input image.
            roi (tuple, optional): Region of interest in the format (x, y, w, h). If specified, only this region will be processed for hand detection. Defaults to None.
            draw (bool, optional): If set to true, draw the hand(s) keypoints and connections. Defaults to True.
            return_handedness (bool, optional): Returns the list of score and label for right handedness.ATTENTION: if the input image is not flipped, returns the label Right for the left hand and vice-versa!!!. Defaults to False.

        Returns:
            frame:  opencv image in BGR with keypoints drawn if draw is set to true
            right_handedness (optional): list of scores and labels for hand handedness.
        """
        '''
        Detects the hands and draws keypoints of the hands given and input image.
        :param: img (opencv image in BGR)
        :param: draw (boolean, draw the keypoint if set to true, default is true)
        :returns: img (opencv image in BGR with keypoints drawn if draw is set to true)
        '''
        green = (0, 255, 0)
        white = (255,255,255)
        self.frame_w = frame.shape[1]
        self.frame_h = frame.shape[0]

        # if ROI is specified, only process the region of interest, otherwise process the whole image
        if roi:
            x, y, w, h = roi
            search_region = frame[y:y+h, x:x+w]
            
            # draw the region of interest (ROI) if specified
            if draw_roi:
                cv2.rectangle(frame_to_draw, (x, y), (x + w, y + h),green,  2)
        else:
            search_region = frame

        imgRGB = cv2.cvtColor(search_region, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)

        # if hands are detected
        if self.results.multi_hand_landmarks:

            # for each hand
            for handLMs in self.results.multi_hand_landmarks:
                # applies the offset to fit roi landmarks in the original frame
                if roi:
                    width_hight = frame.shape[1], frame.shape[0]

                    fit_roi_landmarks_to_frame(
                        landmarks=handLMs.landmark, 
                        pixel_frame_size=width_hight, 
                        pixel_region_x_y_w_h=roi
                        )

            return self.results.multi_handedness

    def create_pixel_landmark_list(self)->list:
        self.lm_list = []

        if self.hand_landmarks:
            for id, lm in enumerate(self.hand_landmarks):
                x, y = (lm.x * self.frame_w), (lm.y * self.frame_h)
                self.lm_list.append([id, int(x), int(y)])
        return self.lm_list

    def draw_skeleton(self, frame):
        connections = HAND_CONNECTIONS
        for start, end in connections:
            cv2.line(
                frame,
                self.lm_list[start][1:3],
                self.lm_list[end][1:3],
                S.white,
                2
            )
        for id, *xy in self.lm_list:
            cv2.circle(frame, xy, 4, S.white, -1)

if __name__ == '__main__':
    pass
    
