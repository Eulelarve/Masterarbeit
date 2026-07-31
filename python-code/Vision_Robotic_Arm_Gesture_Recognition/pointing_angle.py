import cv2
import time
import math
import json
import socket

import pyrealsense2 as rs
import numpy as np
from datetime import datetime


from own_functions import insert, keep_rect_inside, map_threshold
from coordinates_handler import angle_between_points, draw_angle_between_points


from HandDetectorModule_changed import HandDetector as hdm
from PoseDetectorModule_changed import poseDetector as pdm
from analyse import SaveFrameStatus, save_list_to_file, find_files

import settings as S

def find_pointing_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance:int, frame=None ,drawing_2d_points=None, draw=False, left_is_minus=True, ):
    
    arm_azimuth = _find_pointing_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance, left_is_minus, )

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

def _find_pointing_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance:int, left_is_minus:bool):
    hand = angle_3d_points[i_hand]
    shulder = angle_3d_points[i_shulder]
    if None in [hand ,shulder]:
        return None
    
    x1,y1,z1 = hand[1:] 
    x2,y2,z2 = shulder[1:] 
    x3,y3,z3 = x2,y2,z2
    # referenz line to the front (z - ref)
    z3 += -1 # ajust deepth of the referenz axis/point

    hand_shulder_dist = math.dist((x1,y1,z1),(x2,y2,z2)) # if shoulder and hand are overlapping in the frame
    if zero_degree_distance >= hand_shulder_dist:
        return  0
    
    arm_azimuth = angle_between_points((x1,z1), (x2,z2), (x3,z3)) # take just x and y dimension, not z (hight)
    # to different angle directions
    if x1 < x2: # hand nach links side
        arm_azimuth *= 1 -2*left_is_minus  
    else:
        arm_azimuth *= -1 +2*left_is_minus 
    return arm_azimuth


def correct_pointing_angle(angle:float,hand_side:str,mirrowed_frame:bool):
    if angle is None:
        return None
    max_correction = 15 # degree
    sliding_factor = (90-abs(angle))/90
    correction = sliding_factor * max_correction

    if mirrowed_frame:
        correction *= -1

    if hand_side == 'left':
        new_angle = angle - correction
    elif hand_side == 'right':
        new_angle = angle + correction

    return new_angle

def clip_pointing_angle(angle, real_depth):
    res = S.real_depth_angle_resulutuin
    if angle is None:
          return None
    if real_depth:
        angle = round(angle/res)*res
        angle = np.clip(angle, -90, +90)
    else:                 
        angle = map_threshold(angle,(-75,-25,25,75),(-90,-45,0,45,90))
    return angle