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

def find_pointing_angle2(angle_3d_points,i_hand,i_shulder, zero_degree_distance:int, frame ,drawing_2d_points, draw, left_is_minus,
                        room_size:tuple,origin:tuple, start_point:tuple, resulution:float ):
    arm_azimuth = find_arm_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance, left_is_minus, )
    if draw:
        draw_arm_angle(frame,i_hand,i_shulder, drawing_2d_points, arm_azimuth)
    p1 = origin
    p2 = get_room_wall_projection_point(room_size,origin, start_point, arm_azimuth, None, resulution)
    pointing_azimut = angle_between_points()
    return pointing_azimut

def get_room_wall_projection_point(room_size:tuple,origin:tuple, start_point:tuple, azimuth_angle:float, elevation_angle:float, resulution:float)->list:
    """
    follow a slope (ray tracing) in a room on till it hits one wall
    returns the hitting point
    Args:
        room_size (tuple): size of the room in x,y,z direction
        origin (tuple): coordinate origin of the room in x,y,z direction, (0,0,0) is the room bottom left front corner
        start_point (tuple): starting point of the ray tracing, real in x,y,z direction, (0,0,0) is the origin point
        azimuth_angle (float): azimuth angle in degrees
        elevation_angle (float): elevation angle in degrees
        resulution (int): step size of the ray tracing, 
    """
    # input check
    if resulution == 0:
        raise ValueError("Resolution cannot be zero")
    # declatagion of needed values
    right_wall = room_size[0] - origin[0]
    left_wall = - origin[0]
    ceiling = room_size[1] - origin[1]
    floor = - origin[1]
    back_wall = room_size[2] - origin[2]
    front_wall = - origin[2]
    x = origin[0] + start_point[0]
    y = origin[1] + start_point[1]
    z = origin[2] + start_point[2]
    step = resulution
    # ray tracing
    room_diagonal = math.hypot(*room_size)
    max_steps = math.ceil(room_diagonal/step)
    for _ in max_steps:
        # follow slope
        x += math.sin(math.radians(azimuth_angle)) * step
        y += (math.sin(math.radians(elevation_angle)) * step) if elevation_angle else 0
        z += math.cos(math.radians(azimuth_angle)) * step
        # checking room borders
        if x >= right_wall:
            x = right_wall
            return [x,y,z]
        elif x <= left_wall:
            x = left_wall
            return [x,y,z]
        elif y >= ceiling:
            y = ceiling
            return [x,y,z]
        elif y <= floor:
            y = floor
            return [x,y,z]
        elif z >= back_wall:
            z = back_wall
            return [x,y,z]
        elif z <= front_wall:
            z = front_wall
            return [x,y,z]
    # not valide
    return None

def find_pointing_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance:int, frame=None ,drawing_2d_points=None, draw=False, left_is_minus=True, ):
    
    arm_azimuth = find_arm_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance, left_is_minus, )

    if draw:
        draw_arm_angle(frame,i_hand,i_shulder, drawing_2d_points, arm_azimuth)
    
    return arm_azimuth

def find_arm_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance:int, left_is_minus:bool):
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

def draw_arm_angle(frame,i_hand,i_shulder, drawing_2d_points, arm_azimuth):
    p1_2d = drawing_2d_points[i_hand][1:3]
    p2_2d = drawing_2d_points[i_shulder][1:3]
    p3_2d = p2_2d.copy()
    p3_2d[1] += 100 # draw in y direction
    try:
        text = str(round(arm_azimuth)) 
    except:
        text = 'None'
    draw_angle_between_points(frame,text,p1_2d,p2_2d,p3_2d,(-10,-10), S.green)

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