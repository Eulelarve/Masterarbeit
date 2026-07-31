import mediapipe as mp
import numpy as np
import cv2

import time
import math

from own_functions import ValueBuffer, close_to
from coordinates_handler import get_center_of_landmarks, angle_between_points, draw_angle_between_points

class poseDetector():
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
        self.mode = mode  # static image mode
        self.modCompl = modCompl
        self.upBody = upBody
        self.smooth = smooth
        self.segm = segm
        self.smooth_seg = smooth_seg
        self.detCon = detCon  # detection confidence threshold
        self.trackCon = trackCon  # tracking confidence threshold
        self.hand_moving_buffer = ValueBuffer(5)

        self.mpPose = mp.solutions.pose
        self.pose = self.mpPose.Pose(static_image_mode=self.mode,
                                     model_complexity=self.modCompl,
                                     smooth_landmarks=self.smooth,
                                     enable_segmentation=self.segm,
                                     smooth_segmentation=self.smooth_seg,
                                     min_detection_confidence=self.detCon,
                                     min_tracking_confidence=self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils
    


    def findPose(self, frame, frame_to_draw=None, draw=True):
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

        if self.results.pose_landmarks:
            if draw:
                self.mpDraw.draw_landmarks(
                    frame_to_draw, self.results.pose_landmarks, self.mpPose.POSE_CONNECTIONS)
        return frame

    def findPosePosition(self, frame, additional_info=False, draw=True):
        '''
        Given and image, returns the pose keypoints position in the format of a list of lists
        [[id_point0, x_point0, y_point0], ...]
        If additional info is True, returns a list of list in the format
        [[id_point0, x_point0, y_point0, zpoint0, visibility], ...]

        Keypoints list  are shown on this site: https://google.github.io/mediapipe/images/mobile/pose_tracking_full_body_landmarks.png

        :param: additional_info (returns z and visibility in the keypoint list. Default is False)
        :param: frame(opencv BGR image)
        :draw: bool (draws circles over the keypoints. Default is True)

        :returns: 
            lm_list (list of lists of keypoints)
            img
        '''
        self.lm_list = []
        h, w, c = frame.shape

        if self.results.pose_landmarks:
            pose = self.results.pose_landmarks
            for id_point, lm in enumerate(pose.landmark):

                cx, cy = int(lm.x * w), int(lm.y * h)
                if additional_info:
                    cz = lm.z
                    vis = lm.visibility
                    self.lm_list.append([id_point, cx, cy, cz, vis])
                else:
                    self.lm_list.append([id_point, cx, cy])

                if draw:
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

        return self.lm_list

    def find_specific_points(self):
        landmarks = self.lm_list
        hand_points = self.get_hand_points('top')
        self.hand_center = get_center_of_landmarks(landmarks,hand_points[1:3]) # just take 17, 19 (left) or 18, 20 (right) to get the hand center
        self.hand_center.insert(0, hand_points[0]) # [15 or 16, x, y]  while 15 left, 16 right hand center
        if 15 in hand_points: # left hand
            self.shulder = landmarks[11] # left shulder
            self.hip = landmarks[23]
            self.hand_side = 'left'
        elif 16 in hand_points: # right hand
            self.shulder = landmarks[12] # right shulder
            self.hip = landmarks[24]
            self.hand_side = 'right'

    
    def calibrate_arm_length(self,time_to_calibrate=2.0, max_rel_hight_diff=1/4):
        left_hand_center = get_center_of_landmarks(self.lm_list,[17,19])
        right_hand_center = get_center_of_landmarks(self.lm_list,[18,20])
        left_shulder = self.lm_list[11][1:]
        right_shulder = self.lm_list[12][1:]
        left_hip = self.lm_list[23][1:]
        
        max_y_pixel_diff = (left_hip[1] - left_shulder[1]) * max_rel_hight_diff
        if close_to(max_y_pixel_diff, right_shulder,
                    left_hand_center,right_hand_center,left_shulder):
            
            if self.calibranion_start_time > time_to_calibrate:
                left_arm = math.dist(left_hand_center,left_shulder)
                right_arm = math.dist(right_hand_center,right_shulder)
                self.arm_len = (left_arm + right_arm)/2

        else:
            self.calibranion_start_time = time.perf_counter()


        


    def find3DPosePosition(self, additional_info=False, draw=False):
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
            for id_point, lm in enumerate(pose.landmark):
                cx, cy, cz = lm.x, lm.y, lm.z

                if additional_info:
                    vis = lm.visibility
                    self.lm_3dlist.append([id_point, cx, cy, cz, vis])
                else:
                    self.lm_3dlist.append([id_point, cx, cy, cz])

            if draw:
                self.mpDraw.plot_landmarks(
                    self.results.pose_world_landmarks, self.mpPose.POSE_CONNECTIONS)

        return self.lm_3dlist

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
        # # checks if keypoints values are correct
        # assert i1 >= 0 and i1 <= 32, f"p1 must be >=0 and <=32"
        # assert i2 >= 0 and i2 <= 32, f"p2 must be >=0 and <=32"
        # assert i3 >= 0 and i3 <= 32, f"p3 must be >=0 and <=32"
        

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


    def get_hand_points(self, left_right_top='top', mirrored=False):
        """ choose between left, right or top hand based on the pose landmarks
        Args:
            pose_landmarks: list of pose landmarks
            left_right_top: 'left', 'right' or 'top'
            mirrored: if the image is mirrored, left and right are switched
        Returns:
            hand_center: index of the chosen wrist landmark (15 for left, 16 for right)
        
        """
        pose_landmarks = self.lm_list
            
        # only the first leter is capital letter, so it is uniform for all spelling options
        left_right_top = left_right_top.capitalize() 
        hand_center = None
        left_hand_points = [ 15,17,19, 21 ] # left hand landmarks from mediapipe pose
        right_hand_points = [ 16,18,20, 22 ] # right hand landmarks from mediapipe pose

        if left_right_top == "Top":
            hand_points = self.get_upper_points([left_hand_points, right_hand_points])

        elif left_right_top == "Left":
            hand_points = left_hand_points if not mirrored else right_hand_points

        elif left_right_top == "Right":
            hand_points = right_hand_points if not mirrored else left_hand_points
        else:
            print(f"Invalid hand selection mode: {left_right_top}. Please choose 'top', 'left' or 'right'.")
        
        return hand_points

    def get_upper_body_length(self):
        if self.lm_list:
            marks = self.lm_list
        elif self.lm_3dlist:
            marks = self.lm_3dlist
        else:
            raise Exception('Landmark list is empty, use this function only after using the FindPose and FindPosePosition methods')
        x_y_shulder = (np.array(marks[12][1:3]) + marks[13][1:3]) / 2 # midle between ledt and right sholder side
        x_y_hip = (np.array(marks[24][1:3]) + marks[23][1:3]) / 2 

        # compute upper body lenght as L2 norm between the upper palm midpoint and lower palm midpoint
        body_len = np.linalg.norm(x_y_shulder - x_y_hip, ord=2)
        return body_len

# ---------------------------------------------------------------
# MAIN SCRIPT EXAMPLE FOR REAL-TIME POSE TRACKING USING A WEBCAM
# ---------------------------------------------------------------


def main(camera_source=0, show_fps=True, verbose=False):

    assert camera_source >= 0, f"source needs to be greater or equal than 0\n"

    ctime = 0  # current time (used to compute FPS)
    ptime = 0  # past time (used to compute FPS)

    cv2.setUseOptimized(True)

    # capture the input from the default system camera (camera number 0)
    cap = cv2.VideoCapture(camera_source)
    detector = poseDetector(detCon=0.7, trackCon=0.7, modCompl=1)

    if not cap.isOpened():  # if the camera can't be opened exit the program
        print("Cannot open camera")
        exit()

    while True:  # infinite loop for webcam video capture

        ret, frame = cap.read()  # read a frame from the webcam

        if not ret:  # if a frame can't be read, exit the program
            print("Can't receive frame from camera/stream end")
            break

        frame = detector.findPose(frame=frame,draw=False)
        lm_list = detector.findPosePosition(
            frame, additional_info=True, draw=False)
        lm_3dlist = detector.find3DPosePosition()

        if len(lm_list) > 0 and len(lm_3dlist) > 0:
            elbow_angle_3d = detector.findAngle(
                frame, 12, 14, 16, angle3d=True, draw=True)


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
    main(camera_source=1)
