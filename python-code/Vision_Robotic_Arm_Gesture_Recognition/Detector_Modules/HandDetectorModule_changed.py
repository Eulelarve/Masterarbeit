import mediapipe as mp
import matplotlib.pyplot as plt
import numpy as np
import cv2

import time

from own_funktions import fit_frameregion_landmoars_to_frame

class HandDetector():
    def __init__(self, mode=False, maxHands=2, modCompl=1, detCon=0.5, trackCon=0.5):
        """Hand detector class that is used to detect the hand keypoints.

        Args:
            mode (bool, optional): If set to false, the solution treats the input images as a video stream. It will try to detect hands in the first input images, and upon a successful detection further localizes the hand landmarks. In subsequent images, once all max_num_hands hands are detected and the corresponding hand landmarks are localized, it simply tracks those landmarks without invoking another detection until it loses track of any of the hands. This reduces latency and is ideal for processing video frames. If set to true, hand detection runs on every input image, ideal for processing a batch of static, possibly unrelated, images. Default to false.
            
            maxHands (int, optional): Maximum number of hands to detect. Default to 1.
            
            modCompl (int, optional): Complexity of the hand landmark model: 0 or 1. Landmark accuracy as well as inference latency generally go up with the model complexity. Default to 1.
            
            detCon (float, optional): Minimum confidence value ([0.0, 1.0]) from the hand detection model for the detection to be considered successful. Default to 0.5.
            
            trackCon (float, optional): Minimum confidence value ([0.0, 1.0]) from the landmark-tracking model for the hand landmarks to be considered tracked successfully, or otherwise hand detection will be invoked automatically on the next input image. Setting it to a higher value can increase robustness of the solution, at the expense of a higher latency. Ignored if static_image_mode is true, where hand detection simply runs on every image. Default to 0.5.
        """
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

    ### added methods

    def choose_hand(self, left_right_top='top'):
        """ Chooses the hand landmarks and index to return based on the specified mode.
        Args:
            left_right_top (str, optional): Mode for selecting hand landmarks. 
                "top" - selects the hand whose center is highest in the image.
                "left" - selects the homans left hand.
                "right" - selects the homans right hand.
                Default is "top".
        Returns:
            hand_landmarks: The selected hand landmarks or None if no hand is detected.
            index: The index of the selected hand in the multi_hand_landmarks list, or None if no hand is detected.
        """
        if self.results.multi_hand_landmarks and self.results.multi_handedness:
            
            # only the first leter is capital letter, so if fits to the Mediapipe label format
            left_right_top = left_right_top.capitalize() 

            #--------------------------------------------------
            # Only one hand detected, return it regardless of the mode
            #--------------------------------------------------

            if len(self.results.multi_hand_landmarks) == 1:
                index = 0
                return self.results.multi_hand_landmarks[0], index 
            
            # --------------------------------------------------
            # Oberste Hand
            # --------------------------------------------------

            elif left_right_top == "Top":

                top_hand, index = self._get_topmost_hand(
                    self.results.multi_hand_landmarks
                )

                if top_hand is not None:
                    return top_hand, index

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
                        return hand_landmarks, index
            else:
            # --------------------------------------------------
            # Invalid mode
            # --------------------------------------------------

                print(f"Invalid hand selection mode: {left_right_top}. Please choose 'top', 'left' or 'right'.")
        
        return None, 0

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

    def findHands(self,frame, roi=None, draw_landmarks=True, draw_roi=True, return_handedness=False):
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
        

        # if ROI is specified, only process the region of interest, otherwise process the whole image
        if roi:
            x, y, w, h = roi
            search_region = frame[y:y+h, x:x+w]
            
            # draw the region of interest (ROI) if specified
            if draw_roi:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
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

                    fit_frameregion_landmoars_to_frame(
                        landmarks=handLMs.landmark, 
                        pixel_frame_size=width_hight, 
                        pixel_region_x_y_w_h=roi
                        )
                # draw the hand keypoints and connections
                if draw_landmarks:
                    self.mpDraw.draw_landmarks(frame, handLMs,
                                            self.mpHands.HAND_CONNECTIONS,)
                                            # self.mpDraw.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=4),
                                            # self.mpDraw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2))
    
        if return_handedness:
            return frame, self.results.multi_handedness
        else:
            return frame

    def findHandPosition(self, frame, hand_choice:str='top', draw=True):
        '''
        Given and image, returns the hand keypoints position in the format of a list of lists
        [[id_point0, x_point0, y_point0], ..., [id_point19, x_point19, y_point19]]
        The number of hand keypoints are 20 in total.
        Keypoints list and relative position are shown in the example notebook and on this site: https://google.github.io/mediapipe/solutions/hands.html

        :param: img (opencv BGR image)
        :param: hand_num (hand id number to detect, default is zero)
        :draw: bool (draws circles over the hand keypoints, default is true)

        :returns: 
            lm_list (list of lists of keypoints)
            img
        '''
        self.lm_list = []
        h, w, c = frame.shape
        if self.results.multi_hand_landmarks:
            handLMs, i = self.choose_hand(hand_choice)
            for id_point, lm in enumerate(handLMs.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.lm_list.append([id_point, cx, cy])
                if draw:
                    cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

        return self.lm_list, frame

    def findHand3DPosition(self, hand_choice:str='top', draw=False):
        '''
        Find the hand 3d positions on the referred detected hand in real-world 3D coordinates 
        that are in meters with the origin at the hand's approximate geometric center.
        Please refer to the documentation for further details: 
        https://google.github.io/mediapipe/solutions/hands.html#multi_hand_world_landmarks


        :param: hand_num (hand id number to detect, default is zero)
        :draw: bool (draws a 3d graph of the predicted locations in world coordinates of the hand keypoints, default is False)

        :returns: list of lists of 3d hand keypoints in the format [[id_point, x_point,y_point,z_point]]
        '''
        self.lm3d_list = []
        if self.results.multi_hand_world_landmarks:
            hand3DLMs, i = self.choose_hand(hand_choice)
            for id_point, lm in enumerate(hand3DLMs.landmark):
                self.lm3d_list.append([id_point, lm.x, lm.y, lm.z])
            if draw:
                self.mpDraw.plot_landmarks(
                    hand3DLMs, self.mpHands.HAND_CONNECTIONS, azimuth=5)
        return self.lm3d_list

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
        if self.results.multi_hand_landmarks:
            hand = self.results.multi_hand_landmarks[0]
            lm1 = hand.landmark[landmark_id1]
            lm2 = hand.landmark[landmark_id2]
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
    
    def open_or_close(self, frame=None, draw=True):
        """ returns: 1: open hand: blue or 0: closed hand: red
        """
        red = (0, 0, 255)
        blue = (255, 0, 0)
        hand_len = self.get_distance(0, 5)
        hand_width = self.get_distance(5, 17 )
        distance_wrist_index = self.get_distance(0, 8)
        distance_thump_pinky = self.get_distance(4, 20)
        color = blue
        show_distance = (0, 8)

        if hand_len > hand_width:   # hand from the side, check length
            if distance_wrist_index > 1.2 * hand_len: # open hand
                state = 1
            else: # closed hand
                state = 0
                show_distance = (0, 5)
                color = red
        else:   # hand from the fromt, check width
            if distance_thump_pinky > 1.2 * hand_width: # open hand
                state = 1
                show_distance = (4, 20)
            else: # closed hand
                state = 0
                show_distance = (5, 17)
                color = red

        if draw and frame is not None:
            self.get_distance(show_distance[0], show_distance[1], frame=frame, draw=True, color=color)
        
        return state

    
    def findHandAperture(self, frame, verbose=False, show_aperture=True, aperture_range: list = [0.4, 1.7]):
        '''
        Finds the normalized hand aperture as distance between the mean point of the hand tips and the mean wrist and thumb base point divided by the palm lenght.

        Parameters
        ----------
        frame: opencv image array
            contains frame to be processed
        verbose: bool
            If set to True, prints the hand aperture value on the frame (default is False)
        show_aperture: bool
            If set to True, show the hand aperture with a line
        aperture_range: list of 2 floats containing the min aperture and max aperture to remap from 0 to 1

        default: [0.4, 1.7] gets remapped to [0, 1] 

        Returns
        --------
        frame, hand aperture (aperture)
        In case the aperture can't be computed, the value of aperture will be None
        '''
        aperture = None

        thumb_cmc_lm_array = np.array(self.lm_list[1][1:])
        wrist_lm_array = np.array(self.lm_list[0][1:])
        lower_palm_midpoint_array = (thumb_cmc_lm_array + wrist_lm_array) / 2

        index_mcp_lm_array = np.array(self.lm_list[5][1:])
        pinky_mcp_lm_array = np.array(self.lm_list[17][1:])
        upper_palm_midpoint_array = (
            index_mcp_lm_array + pinky_mcp_lm_array) / 2

        # compute palm lenght as L2 norm between the upper palm midpoint and lower palm midpoint
        palm_len = np.linalg.norm(
            upper_palm_midpoint_array - lower_palm_midpoint_array, ord=2)
        # compute palm width as L2 norm between the index mcp and pinky mcp
        palm_width = np.linalg.norm(
            index_mcp_lm_array - pinky_mcp_lm_array, ord=2)

        if palm_len > palm_width: # means hand is shown from the side
            # 4 finger tips
            index_tip_array = np.array(self.lm_list[8][1:])
            middle_tip_array = np.array(self.lm_list[12][1:])
            ring_tip_array = np.array(self.lm_list[16][1:])
            pinky_tip_array = np.array(self.lm_list[20][1:])
            
            hand_tips = np.array([index_tip_array,
                                middle_tip_array,
                                ring_tip_array,
                                pinky_tip_array])

            tips_midpoint_array = np.mean(hand_tips, axis=0)

            # compute hand aperture length as L2norm between hand tips midpoint and lower palm midpoint
            # normalize by palm length computed before
            hand_len = np.linalg.norm(
                tips_midpoint_array - lower_palm_midpoint_array, ord=2)
            aperture = hand_len / palm_len
        else: # means hand is shown from the front
            # compute hand aperture width
            thump_tip_array = np.array(self.lm_list[4][1:])
            pinky_tip_array = np.array(self.lm_list[20][1:])
            thump_to_pinly_tip_distance = np.linalg.norm(
                thump_tip_array - pinky_tip_array, ord=2)
            aperture = thump_to_pinly_tip_distance / palm_width

        aperture_norm = np.round(
            np.interp(aperture, aperture_range, [0, 100]), 1)

        if verbose:
            cv2.putText(frame, "HAND APERTURE:" + str(aperture_norm), (10, 40),
                        cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 1, cv2.LINE_AA)
        if show_aperture:
            # frame = cv2.line(frame, tuple(tips_midpoint_array.astype(int)),
            #                  tuple(lower_palm_midpoint_array.astype(int)), (255, 0, 0), 3)
            frame = cv2.line(frame, tuple(thump_tip_array.astype(int)),
                             tuple(pinky_tip_array.astype(int)), (255, 0, 0), 3)

        return frame, aperture_norm

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
            frame=frame, hand_num=0, draw=False)

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
    