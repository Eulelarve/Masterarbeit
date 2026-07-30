import cv2
import time
import math
import json
import socket

import pyrealsense2 as rs
import numpy as np
from datetime import datetime


from own_functions import insert, keep_rect_inside
from coordinates_handler import angle_between_points, draw_angle_between_points


from HandDetectorModule_changed import HandDetector as hdm
from PoseDetectorModule_changed import poseDetector as pdm
from analyse import SaveFrameStatus, save_list_to_file, find_files

import settings as S

def find_pointing_angle(angle_3d_points,i_hand,i_shulder, frame=None ,drawing_2d_points=None, draw=False, left_is_minus=True):
    hand = angle_3d_points[i_hand]
    shulder = angle_3d_points[i_shulder]
    if None in [hand ,shulder]:
        return None
    
    x1,y1,z1 = hand[1:] 
    x2,y2,z2 = shulder[1:] 
    x3,y3,z3 = x2,y2,z2
    # referenz line to the front (z - ref)
    z3 += -1 # ajust deepth of the referenz axis/point

    arm_azimuth = angle_between_points((x1,z1), (x2,z2), (x3,z3)) # take just x and y dimension, not z (hight)
    # to different angle directions
    if x1 < x2: # hand nach links side
        arm_azimuth *= 1 -2*left_is_minus  
    else:
        arm_azimuth *= -1 +2*left_is_minus 
        
    if draw:
        p1_2d = drawing_2d_points[i_hand][1:3]
        p2_2d = drawing_2d_points[i_shulder][1:3]
        p3_2d = p2_2d.copy()
        p3_2d[1] += 100 # draw in y direction
        try:
            text = str(round(arm_azimuth)) 
        except:
            text = 'None'
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



  