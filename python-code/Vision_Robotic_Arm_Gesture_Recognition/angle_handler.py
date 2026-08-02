import cv2
import time
import math
import json
import socket

import pyrealsense2 as rs
import numpy as np
from datetime import datetime


from own_functions import insert, keep_rect_inside, map_threshold
from analyse import SaveFrameStatus, save_list_to_file, find_files

import settings as S

    
def angle_between_points(p1:tuple, p2:tuple, p3:tuple)->float:
    """ 
        calcumates the angle between 2 vectors given by 3 points (2D or 3D)
        p2 is the mittel point / angle point / shared point of the voctors
    """
    v1 = np.array(p1) - np.array(p2)
    v2 = np.array(p3) - np.array(p2)

    angle = np.arccos(
        np.dot(v1, v2) /
        (np.linalg.norm(v1) * np.linalg.norm(v2))
    )

    return np.degrees(angle)

def draw_angle_between_points(frame, text:str, p1:list[int,int] ,p2:list[int,int] ,p3:list[int,int] , text_pos=(-50,+50), color=(255, 255, 255)):
        """ 
            draw lines between points and are angle number next to p2
        """
        cx1, cy1 = p1
        cx2, cy2 = p2
        cx3, cy3 = p3
        
        cv2.circle(frame, (cx1, cy1), 5, (255, 0, 255), -1)
        cv2.circle(frame, (cx2, cy2), 5, (255, 0, 255), -1)
        cv2.circle(frame, (cx2, cy2), 10, (255, 0, 255), 1)
        cv2.circle(frame, (cx3, cy3), 5, (255, 0, 255), -1)
        
        cv2.line(frame, (cx2, cy2), (cx3, cy3), color, 2)
        cv2.line(frame, (cx2, cy2), (cx1, cy1), color, 2)
        
        cv2.putText(frame, text, (cx2 + text_pos[0], cy2 + text_pos[1]),
                    cv2.FONT_HERSHEY_PLAIN, 1, color, 2, cv2.LINE_AA)

def find_pointing_angle2(angle_3d_points,i_hand,i_shulder, frame ,drawing_2d_points, draw, left_is_minus):
    pointing_azimut = None 
    pointing_elevation = None
    arm_azimuth = None
    arm_elevation = None
    shoulder = angle_3d_points[i_shulder]
    if shoulder is not None:
        # set parameters
        resulution = S.step_size_to_find_pointing_angle
        room_size = S.room_size
        origin = S.room_origin  
        zero_degree_distance = S.zero_degree_distance
        start_point = shoulder[1:]
        # arm angle
        arm_azimuth = find_arm_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance, left_is_minus, )
        # room angle (pointing angle)
        pointing_azimut ,pointing_elevation = find_room_angles(room_size,origin, start_point, arm_azimuth, arm_elevation, resulution, left_is_minus)
    if draw:
        draw_arm_angles(frame,i_hand,i_shulder, drawing_2d_points, arm_azimuth, arm_elevation)
    return pointing_azimut ,pointing_elevation

def find_room_angles(room_size:tuple,origin:tuple, start_point:tuple, azimuth_angle:float, elevation_angle:float, resulution:float, left_is_minus:bool) ->tuple[float,float]:
    p1 = rey_tracing_to_room_border(room_size,origin, start_point, azimuth_angle, elevation_angle, resulution)
    room_azimuth = find_azimuth_angle(p1 ,origin, left_is_minus)
    room_elevation = None
    return room_azimuth, room_elevation

def rey_tracing_to_room_border(room_size:tuple,origin:tuple, start_point:tuple, azimuth_angle:float, elevation_angle:float, resulution:float)->list:
    """
    follow (ray tracing) a slope (angles) in a room on till it hits one wall
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
    if azimuth_angle is None:
        return None
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
    for _ in range(max_steps):
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

def find_pointing_angle(angle_3d_points,i_hand,i_shulder, frame=None ,drawing_2d_points=None, draw=False, left_is_minus=True, ):
    zero_degree_distance = S.zero_degree_distance
    arm_azimuth = find_arm_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance, left_is_minus, )
    arm_elevation = None
    if draw:
        draw_arm_angles(frame,i_hand,i_shulder, drawing_2d_points, arm_azimuth, arm_elevation)
    
    return arm_azimuth ,arm_elevation

def find_arm_angle(angle_3d_points,i_hand,i_shulder, zero_degree_distance:int, left_is_minus:bool)->float|None:
    hand = angle_3d_points[i_hand]
    shulder = angle_3d_points[i_shulder]
    if hand is None or shulder is None:
        return None
    
    p1 = hand[1:] 
    p2 = shulder[1:] 
    hand_shulder_dist = math.dist(p1, p2) # if shoulder and hand are overlapping in the frame
    if zero_degree_distance >= hand_shulder_dist:
        return  0
    
    return find_azimuth_angle(p1,p2,left_is_minus)

def find_azimuth_angle(p1:tuple,p2_angle_point:tuple,left_is_minus:bool=True)->float:
    if p1 is None or p2_angle_point is None:
        return None
    # p1
    x1 = p1[0]
    z1 = p1[-1]
    # p2 angle point
    x2 = p2_angle_point[0]
    z2 = p2_angle_point[-1]
    # p3 room refference point
    x3 = x2
    z3 = z2 -1
    arm_azimuth = angle_between_points((x1,z1), (x2,z2), (x3,z3)) # take just x and y dimension, not z (hight)
    # decide the angle directions
    if x1 < x2: # p1 nach links side (-x) of the angle point
        arm_azimuth *= 1 -2*left_is_minus  
    else:
        arm_azimuth *= -1 +2*left_is_minus 
    return arm_azimuth


def draw_arm_angles(frame,i_hand,i_shulder, drawing_2d_points, arm_azimuth, arm_elevation):
    p1_2d = drawing_2d_points[i_hand][1:3]
    p2_2d = drawing_2d_points[i_shulder][1:3]
    p3_2d = p2_2d.copy()
    p3_2d[1] += 100 # draw in y direction
    text = ''
    if arm_azimuth is not None:
        text += str(round(arm_azimuth)) 
    if arm_elevation is not None:
        text += '/' 
        text += str(round(arm_elevation)) 
    if not text:
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