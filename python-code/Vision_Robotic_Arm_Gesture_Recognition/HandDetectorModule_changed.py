import mediapipe as mp
import matplotlib.pyplot as plt
import numpy as np
import cv2
import math
import time
from collections import defaultdict


from own_functions import fit_roi_landmarks_to_frame, ValueBuffer, close_to, ListBuffer, ValueBufferTime
import settings as S


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

        self.pixel_pos_anti_outliner = [ListBuffer(S.position_median_buffer_size, 'median') for _ in self.lm_range]
        self.pixel_pos_smoother = [ListBuffer(S.position_average_buffer_size, 'average') for _ in self.lm_range]

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
                    self.results.multi_handedness
                )):

                    label = (
                        handedness.classification[0].label
                    )

                    if label == desired_label:
                        index = i
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
    
    ### added methods

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
                # draw the hand keypoints and connections
                # if draw_landmarks:
                #     self.mpDraw.draw_landmarks(frame_to_draw, handLMs,
                #                             self.mpHands.HAND_CONNECTIONS,
                #                             self.mpDraw.DrawingSpec(color=green, thickness=1, circle_radius=2),
                #                             self.mpDraw.DrawingSpec(color=white, thickness=2, circle_radius=2))

            return self.results.multi_handedness

    def create_pixel_landmark_list(self)->list:
        self.lm_list = []

        if self.hand_landmarks:
            for id, lm in enumerate(self.hand_landmarks):
                x, y = (lm.x * self.frame_w), (lm.y * self.frame_h)
                self.lm_list.append([id, int(x), int(y)])
            self.disjiggle_pixel_landmark_list()
               
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

    def disjiggle_pixel_landmark_list(self):
        for id, x,y in self.lm_list:
            if S.position_median_buffer_size >= 3:
                x, y = self.pixel_pos_anti_outliner[id].add_and_get((x, y))
            if S.position_average_buffer_size >= 2:
                x, y = self.pixel_pos_smoother[id].add_and_get((x, y))
            self.lm_list[id][:] = id, int(x), int(y)

    # def get_biggest_distance_in_one_hand(self, frame=None,  draw=True):
    #     '''
    #     Computes the biggest distance between two hand keypoints in the detected hand.
    #     This can be used as a simple measure of the hand size or to estimate the distance of the hand to the camera.

    #     :returns: biggest distance in pixels between two hand keypoints
    #     '''
    #     p0 = 0,0
    #     p1 = 0,0
    #     biggest_distance = 0
    #     if self.results.multi_hand_landmarks:
    #         hand = self.results.multi_hand_landmarks[0]
    #         for i in range(len(hand.landmark)):
    #             for j in range(i + 1, len(hand.landmark)):
    #                 lm1 = hand.landmark[i]
    #                 lm2 = hand.landmark[j]
    #                 distance = ((lm1.x - lm2.x) ** 2 + (lm1.y - lm2.y) ** 2) ** 0.5
    #                 if distance > biggest_distance:
    #                     biggest_distance = distance
    #                     p0 = (int(lm1.x * frame.shape[1]), int(lm1.y * frame.shape[0]))
    #                     p1 = (int(lm2.x * frame.shape[1]), int(lm2.y * frame.shape[0]))
    #     if draw and frame is not None:
    #         cv2.line(frame, p0, p1, (255, 0, 0), 3)
    #         # cv2.putText(frame, f"Biggest distance: {biggest_distance:.2f}", (10, 70), cv2.FONT_HERSHEY_PLAIN, 2,
    #                     # (255, 255, 255), 1)
    #     return biggest_distance
    
    def get_distance(self, landmark_id1, landmark_id2, frame=None, draw=False, color=(255, 0, 0)):
        '''
        Computes the distance between two hand keypoints in the detected hand.

        :param: landmark_id1 (int): id of the first landmark (0-20)
        :param: landmark_id2 (int): id of the second landmark (0-20)
        :param: frame (opencv image in BGR, optional): if provided, draws a line between the two landmarks and shows the distance value on the frame
        :param: draw (bool, optional): if set to true and frame is provided, draws a line between the two landmarks and shows the distance value on the frame

        :returns: distance in pixels between the two specified hand keypoints
        '''
        distance = None
        p0 = 0,0
        p1 = 0,0
        if self.hand_landmarks:
            lm1 = self.hand_landmarks[landmark_id1]
            lm2 = self.hand_landmarks[landmark_id2]
            if frame is not None:
                p0 = (int(lm1.x * frame.shape[1]), int(lm1.y * frame.shape[0]))
                p1 = (int(lm2.x * frame.shape[1]), int(lm2.y * frame.shape[0]))
                distance_in_pixels = ((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2) ** 0.5
                distance = distance_in_pixels
            else:
                distance = ((lm1.x - lm2.x) ** 2 + (lm1.y - lm2.y) ** 2) ** 0.5
        
        if draw and frame is not None and distance is not None:
            cv2.line(frame, p0, p1, color, 3)
            # cv2.putText(frame, f"Distance: {distance:.2f}", (10, 70), cv2.FONT_HERSHEY_PLAIN, 2,
            #             (255, 255, 255), 1)
        
        return distance
    
    def get_distance_from_list(self, landmark_id1, landmark_id2, frame=None, draw=False, color=(255, 0, 0)):
        '''
        Computes the distance between two hand keypoints in the detected hand.

        :param: landmark_id1 (int): id of the first landmark (0-20)
        :param: landmark_id2 (int): id of the second landmark (0-20)
        :param: frame (opencv image in BGR, optional): if provided, draws a line between the two landmarks and shows the distance value on the frame
        :param: draw (bool, optional): if set to true and frame is provided, draws a line between the two landmarks and shows the distance value on the frame

        :returns: distance in pixels between the two specified hand keypoints
        '''
        distance = None
        if self.lm_list:
            p0 = self.lm_list[landmark_id1][1:]
            p1 = self.lm_list[landmark_id2][1:]
            if frame is not None:
                distance_in_pixels = ((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2) ** 0.5
                distance = distance_in_pixels
        
        if draw and frame is not None and distance is not None:
            cv2.line(frame, p0, p1, color, 3)
            # cv2.putText(frame, f"Distance: {distance:.2f}", (10, 70), cv2.FONT_HERSHEY_PLAIN, 2,
            #             (255, 255, 255), 1)
        
        return distance
    
    def open_or_close_distance_dif(self, frame=None, draw=True, min_distance_difference=1, time_difference=0.8):# test 1.5 normal 0.8
        wrist_finger_tip = (0, 12)
        thump_pinky = (4, 20)
        red = (0, 0, 255)
        blue = (255, 0, 0)

        key = str(min_distance_difference)+str(time_difference)
        self.no_hand_counter = 0
        # get distance
        distance = max(self.get_distance(*wrist_finger_tip), self.get_distance(*thump_pinky))
        # buffering
        if getattr(self, "dist_smoother", None) is None:
            self.dist_smoother = defaultdict(lambda: ValueBuffer(3))
            self.dist_and_time_buffer = defaultdict(lambda: ValueBufferTime(time_difference))
            self.is_hand_open = 1 # initialisie with hand opening
        distance = self.dist_smoother[key].add_and_get_median(distance)
        self.dist_and_time_buffer[key].add(distance)

        # calcumation
        rel_dif = abs(self.dist_and_time_buffer[key].difference / self.dist_and_time_buffer[key].min)
        # desision
        if rel_dif >= min_distance_difference: # hand startus change
            if self.dist_and_time_buffer[key].i_max > self.dist_and_time_buffer[key].i_min: 
                # max follows min value
                self.is_hand_open = 1 # hand opening
            else:           
                # min follows max value
                self.is_hand_open = 0 # hand closing

        # drawing
        color = red
        if self.is_hand_open:
            color = blue
        if draw and frame is not None:
            self.get_distance(*wrist_finger_tip, frame=frame, draw=True, color=color)
            self.get_distance(*thump_pinky, frame=frame, draw=True, color=color)
        
        return self.is_hand_open
    
    def buffer_clear(self):
        if getattr(self, "dist_smoother", None) is not None:
            for key in self.dist_smoother.keys():
                self.dist_smoother[key].clear()
                self.dist_and_time_buffer[key].clear()
    
    def no_hand_count(self, frames_for_bo_hand:int ,add=1):
        self.no_hand_counter += add
        if self.no_hand_counter >= frames_for_bo_hand:
            return True
        return False 

    # def open_or_close_len_width_thr(self, frame=None, draw=True, use_len_if_larger_then_width=1, hand_opening_factor = 1.4, buffer_size=10):
    #     """ returns: 1: open hand: blue or 0: closed hand: red
    #     """
    #     red = (0, 0, 255)
    #     blue = (255, 0, 0)
    #     hand_len = (0, 9)
    #     hand_width = (5, 17) 
    #     wrist_finger_tip = (0, 12)
    #     thump_pinky = (4, 18) # thump 1-4, pinky 17-20


    #     self.no_hand_counter = 0

    #     # create buffer
    #     if getattr(self, "status_smoother", None) is None:
    #         self.status_smoother = ValueBuffer(buffer_size)


        

    #     measurments = [
    #         (hand_len, red,0, hand_opening_factor),                                 # a hand colsed condition
    #         (hand_width, red,0, hand_opening_factor*use_len_if_larger_then_width),  # a hand colsed condition
    #         (wrist_finger_tip, blue,1, 1),                                          # a hand opened condition
    #         (thump_pinky, blue,1, 1*use_len_if_larger_then_width)                   # a hand opened condition
    #     ]

    #     show_distance:list = None
    #     biggest:int = 0
    #     won_status:int = None
    #     for line, line_color, status, weighting in measurments:
    #         value = self.get_distance(*line) * weighting 
    #         # status with biggest value winns! value is distance times the weighting factor
    #         if value > biggest:
    #             biggest = value
    #             show_distance = line
    #             color = line_color
    #             won_status = status
        
    #     self.is_hand_open = self.status_smoother.add_and_get_most_frequently(won_status)

    #     if draw and frame is not None:
    #         self.get_distance(*show_distance, frame=frame, draw=True, color=color)
        
    #     return self.is_hand_open

    def open_or_close_aperture_thr(self,frame, thr_open=75, thr_closed = 65, buffer_size=S.hand_status_buffer_size, draw_aperture=False):
        key = str(thr_open)+str(thr_closed)
        self.no_hand_counter = 0

        # create buffer
        if getattr(self, "status_smoother", None) is None:
            self.status_smoother = defaultdict(lambda: ValueBuffer(buffer_size))

        aperture, aperture_line = self.findHandAperture()
        
        status = self.is_hand_open # stay like it is
        if aperture is not None:
            if aperture >= thr_open:
                status = 1 # open hand
            elif aperture <= thr_closed:
                status = 0 # closed hand

        if draw_aperture:
            cv2.line(frame,*aperture_line, S.blue if status else S.red, 3)

        self.status_smoother[key].add(status)
        new_status = self.status_smoother[key].atleast(S.hand_status_buffer_atleast)
        if new_status is not None:
            self.is_hand_open = new_status

        return self.is_hand_open
        
    def findHandAperture(self, aperture_range_len = [0.5, 1.7], aperture_range_width = [0.7, 1.7])->tuple[float,tuple]:
        '''
        Finds the normalized hand aperture as distance between the mean point of the hand tips and the mean wrist and thumb base point divided by the palm lenght.

        Parameters
        ----------
        frame: opencv image array
            contains frame to be processed
       
        show_aperture: bool
            If set to True, show the hand aperture with a line
        aperture_range: list of 2 floats containing the min aperture and max aperture to remap from 0 to 1

        default: [0.4, 1.7] gets remapped to [0, 1] 

        Returns
        --------
        frame, hand aperture (aperture)
        In case the aperture can't be computed, the value of aperture will be None
        '''
        aperture_len_norm = None
        aperture_wid_norm = None
        # hand length
        wrist = self.lm_list[0][1:3]
        middle_mcp = self.lm_list[9][1:3]
        middle_tip = self.lm_list[12][1:3]

        palm_len = math.dist(wrist, middle_mcp)
        hand_len = math.dist(wrist, middle_tip)

        if palm_len > 0:
            aperture_len = hand_len / palm_len
            aperture_len_norm = np.round(np.interp(aperture_len, aperture_range_len, [0, 100]), 1)

        # hand width
        pinky_mcp = self.lm_list[17][1:3]
        index_mcp = self.lm_list[5][1:3]
        thump_tip = np.array(self.lm_list[4][1:3])
        pinky_tip = np.array(self.lm_list[20][1:3])

        palm_width = math.dist(index_mcp, pinky_mcp)
        hand_width = math.dist(thump_tip, pinky_tip)
        
        if palm_width > 0:
            aperture_wid = hand_width / palm_width
            aperture_wid_norm = np.round(np.interp(aperture_wid, aperture_range_width, [0, 100]), 1)

        use_len = hand_len > hand_width * 1.2
        if use_len:
            return aperture_len_norm ,(wrist, middle_tip)
        return aperture_wid_norm ,(thump_tip, pinky_tip)


# ---------------------------------------------------------------
# MAIN SCRIPT EXAMPLE FOR REAL-TIME HAND TRACKING USING A WEBCAM
# ---------------------------------------------------------------

def main(camera_source=0, show_fps=True, verbose=False):

    assert camera_source >= 0, f"source needs to be greater or equal than 0\n"

    ctime = 0  # current time (used to compute FPS)
    ptime = 0  # past time (used to compute FPS)

    cv2.setUseOptimized(True)

    # capture the input from the default system camera (camera number 0)
    cap = cv2.VideoCapture(camera_source)
    detector = HandDetector(detCon=0.7, trackCon=0.7)

    if not cap.isOpened():  # if the camera can't be opened exit the program
        print("Cannot open camera")
        exit()

    while True:  # infinite loop for webcam video capture

        ret, frame = cap.read()  # read a frame from the webcam

        if not ret:  # if a frame can't be read, exit the program
            print("Can't receive frame from camera/stream end")
            break

        frame, handness_list = detector.findHands(frame=frame, return_handedness=True)
        hand_lmlist, frame = detector.findHandPosition(
            frame=frame,  draw=False)

        if len(hand_lmlist) > 0:
            frame, aperture = detector.findHandAperture(
                frame=frame, verbose=True, show_aperture=True)

        # compute the actual frame rate per second (FPS) of the webcam video capture stream, and show it
        ctime = time.perf_counter()
        fps = 1.0 / float(ctime - ptime)
        ptime = ctime

        if show_fps:
            cv2.putText(frame, "FPS:" + str(round(fps, 0)), (10, 400), cv2.FONT_HERSHEY_PLAIN, 2,
                        (255, 255, 255), 1)

        # show the frame on screen
        cv2.imshow("Frame (press 'q' to exit)", frame)

        # if the key "q" is pressed on the keyboard, the program is terminated
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    return


if __name__ == '__main__':
    # change this to zero if you don't have a usb webcam but an in-built camera
    main(camera_source=0)
    