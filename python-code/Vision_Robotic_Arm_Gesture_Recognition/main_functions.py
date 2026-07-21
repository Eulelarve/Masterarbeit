import cv2
import time
import math
import json
import socket

import pyrealsense2 as rs
import numpy as np
from datetime import datetime


from own_functions import angle_between_points, draw_angle_between_points, insert, keep_rect_inside

from HandDetectorModule_changed import HandDetector as hdm
from PoseDetectorModule_changed import poseDetector as pdm
from analyse import SaveFrameStatus, save_list_to_file, find_files

import settings as S

def find_pointing_angle(angle_3d_points,i_hand,i_shulder, frame=None ,drawing_2d_points=None, draw=False, left_is_minus=True):

    p1_3d = angle_3d_points[i_hand][1:3] # take just x and y dimension, not z (hight)
    p2_3d = angle_3d_points[i_shulder][1:3] # take just x and y dimension, not z (hight)
    p3_3d = p2_3d.copy()
    # referenz line to the front (z - ref)
    p3_3d[1] += -1 # ajust deepth of the referenz axis/point

    arm_azimuth = angle_between_points(p1_3d[0:2], p2_3d[0:2], p3_3d[0:2]) # take just x and y dimension, not z (hight)
    # to different angle directions
    if p1_3d[0] < p2_3d[0]: # hand nach links side
        arm_azimuth *= 1 -2*left_is_minus  
    else:
        arm_azimuth *= -1 +2*left_is_minus 
        
    if draw:
        p1_2d = drawing_2d_points[i_hand][1:3]
        p2_2d = drawing_2d_points[i_shulder][1:3]
        p3_2d = p2_2d.copy()
        p3_2d[1] += 100 # draw in y direction
        text = str(round(arm_azimuth))
        draw_angle_between_points(frame,text,p1_2d,p2_2d,p3_2d,(-10,-10), S.green)
    
    return arm_azimuth
    # # p1_3d = angle_3d_points[i_hand][1:]
    # p3_3d = p2_3d.copy()
    # p3_3d[1] = -1 # ajust deepth
    # # p3_3d[1] = +1*ref_point_cam_angle_comp  # ajust y
    
    # arm_azimuth = angle_between_points(p1_3d[0:2], p2_3d[0:2], p3_3d[0:2]) # take just x and y dimension, not z (hight)
    # if draw_angles:
    #     p3_2d = p2_2d.copy()
    #     p3_2d[1] = frame.shape[0] # y = frame size
    #     text = str(round(arm_azimuth))+'z'
    #     draw_angle_between_points(frame,text,hand_center,p2_2d,p3_2d,(-10,-50),color)
