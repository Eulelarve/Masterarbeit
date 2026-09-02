import cv2
import time
import math
import json
import socket

import pyrealsense2 as rs
import numpy as np
from datetime import datetime
from coordinates_handler import rs_pixel_to_3d

from own_functions import insert, keep_rect_inside, map_threshold, ValueBuffer, ListBuffer, close_to
from analyse import SaveFrameStatus, save_list_to_file, find_files

import settings as S

def angle_between_points(p1:tuple, p2:tuple, p3:tuple)->float:
    """ 
        calcumates the angle between 2 vectors given by 3 points (2D or 3D)
        p2 is the mittel point / angle point / shared point of the voctors
    """
    v1 = np.array(p1) - np.array(p2)
    v2 = np.array(p3) - np.array(p2)
    return angle_between_vectors(v1,v2)
  

def angle_between_vectors(v1:tuple, v2:tuple, between_0_and_180_deg = False)->float:
    """ 
        calcumates the angle between 2 vectors (2D or 3D)
    """
    dot = sum(a * b for a, b in zip(v1, v2))

    if len(v1) == 2:
        cross = v1[1] * v2[0] - v1[0] * v2[1]
    else:
        cross = math.sqrt(sum(x ** 2 for x in (
            v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0]
        )))

    if between_0_and_180_deg:
        cross = abs(cross)

    return math.degrees(math.atan2(cross, dot))

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

def find_elevation_angle(p1:tuple,p2_angle_point:tuple):
    if p1 is None or p2_angle_point is None:
        return None

    # p3 room refference point, should be p2 shifted by one meter down
    p3 = list(p2_angle_point)
    p3[1] += 1
    elevation = angle_between_points(p1, p2_angle_point, p3) # take just x and y dimension, not z (hight)
    elevation -= 90 # so 0° is horizontal
    return elevation

def find_azimuth_angle(p1:tuple,p2_angle_point:tuple)->float:
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
    azimuth = angle_between_points((x1,z1), (x2,z2), (x3,z3)) # take just x and y dimension, not z (hight)
    return azimuth





def find_room_angles(room_size:tuple,origin:tuple, start_point:tuple, azimuth_angle:float, elevation_angle:float, resulution:float) ->list[float,float]:
    p1 = rey_tracing_to_room_border(room_size,origin, start_point, azimuth_angle, elevation_angle, resulution)
    # x = origin[0] + start_point[0]
    # y = origin[1] + start_point[1]
    # z = origin[2] + start_point[2]
    # print(origin,p1,x,y,z)#test
    room_azimuth = find_azimuth_angle(p1 ,origin)
    room_elevation = find_elevation_angle(p1, origin)
    return [room_azimuth, room_elevation]

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
    return: 
        (list) x,y,z room coordinats in meter, between (0.0, 0.0, 0.0) and rome_size
    """
    # input check
    if resulution == 0:
        raise ValueError("Resolution cannot be zero")
    if azimuth_angle is None:
        return None
    # declatagion of needed values
    right_wall = room_size[0]
    left_wall = 0
    ceiling = room_size[1]
    floor = 0
    back_wall = room_size[2]
    front_wall = 0
    x = origin[0] + start_point[0]
    y = origin[1] + start_point[1]
    z = origin[2] + start_point[2]
    step = resulution
    # calculate Directional components 
    sin_azi = math.sin(math.radians(azimuth_angle))
    cos_azi = math.cos(math.radians(azimuth_angle))
    sin_ele = math.sin(math.radians(elevation_angle)) if elevation_angle else 0
    cos_ele = math.cos(math.radians(elevation_angle)) if elevation_angle else 1
    # ray tracing
    room_diagonal = math.hypot(*room_size)
    max_steps = math.ceil(room_diagonal/step)
    for _ in range(max_steps):
        # follow slope
        x += step * sin_azi * cos_ele 
        y += step * sin_ele
        z -= step * cos_azi * cos_ele
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

class RoomAngleDetector:
    def __init__(self):
        # settings
        self.room_azemuth_aprox_corection_max = 15 # in degree
        self.mirrowed_frame = True
        self.intersection_distance_pixel = 20
        # take global settings
        self.angle_resulution = S.real_depth_angle_resulutuin
        self.ray_tracing_resulution = S.ray_tracing_step_size
        self.intersection_distance = S.zero_degree_distance
        self.room_size = S.room_size
        self.room_center = S.room_center  
        self.dist_cam_to_room_center = S.dist_cam_to_room_center
        self.cam_angle = S.cam_angle
        # variables
        self.angle_smoother = ListBuffer(S.angle_buffer_size)
        self.arm_angles = [None, None] # arm [azimuth, elewation] angle
        self.room_angles = [None, None] # room [azimuth, elewation] angle
        self.hand_3d:list = None
        self.shoulder_3d:list = None
        self.hand_pixel_xy:list = None 
        self.shoulder_pixel_xy:list = None
        self.draw_frame:object = None
        self.cam_intrinsics:object = None

    def find_room_angles_45_deg_aprox(self, hand_side:str, world_lm_hand:tuple, world_lm_shoulder:tuple , hand_pixel_xy:tuple=None, shoulder_pixel_xy:tuple=None ,draw_frame=None, draw:bool=False):
        """ find the room angle with given mediapipe world landmarks with a resupution 45° by +/- 90"""
        self.hand_pixel_xy = hand_pixel_xy
        self.shoulder_pixel_xy = shoulder_pixel_xy
        self.draw_frame = draw_frame

        self.hand_3d = world_lm_hand
        self.shoulder_3d = world_lm_shoulder
        self.hand_side = hand_side

        if self.pointion_into_camera_check(True):
            self.arm_angles = [None, None]
            self.room_angles = [0, 0]
        else:
            self.find_arm_angles()
            self.aprox_room_azimuth()
            self.room_angles[1] = self.arm_angles[1]
            self.map_room_angles_to_45_deg_steps()

        if draw:
            self.draw_arm_angles()

        return self.room_angles

    def find_room_angle_with_intrinsics(self, cam_intrinsics:object, hand_pixel_xy:tuple, shoulder_pixel_xy:tuple, hand_depth:float, shoulder_depth:float ,draw_frame=None, draw:bool=False):
        self.hand_pixel_xy = hand_pixel_xy
        self.shoulder_pixel_xy = shoulder_pixel_xy
        self.draw_frame = draw_frame

        self.cam_intrinsics = cam_intrinsics
        self.find_3d_hand_shoulder_with_depth(hand_depth, shoulder_depth)
        if self.pointion_into_camera_check():
            self.arm_angles = [None, None]
            self.room_angles = [0, 0]
        else:
            # arm angle
            self.find_arm_angles()
            # room angle (pointing angle)
            start_point = self.shoulder_3d.copy()
            start_point[2] -= self.dist_cam_to_room_center
            self.room_angles = find_room_angles(self.room_size, self.room_size, start_point, *self.arm_angles, self.ray_tracing_resulution, True)

        if draw:
            self.draw_arm_angles()

        return self.room_angles

    def find_room_angle_with_depth_frame(self,depth_frame:object, hand_pixel_xy:tuple, shoulder_pixel_xy:tuple ,draw_frame=None, draw:bool=False):
        self.hand_pixel_xy = hand_pixel_xy
        self.shoulder_pixel_xy = shoulder_pixel_xy
        self.draw_frame = draw_frame

        self.find_3d_hand_shoulder_with_depth_frame(depth_frame)
        if self.hand_3d is None or self.shoulder_3d is  None:
            self.arm_angles = [None, None]
            self.room_angles = [None, None]
        elif self.pointion_into_camera_check():
            self.arm_angles = [None, None]
            self.room_angles = [0, 0]
        else:
            # arm angle
            self.find_arm_angles()
            # room angle (pointing angle)
            start_point = self.shoulder_3d.copy()
            start_point[2] -= self.dist_cam_to_room_center
            self.room_angles = find_room_angles(self.room_size, self.room_center, start_point, *self.arm_angles, self.ray_tracing_resulution)
            self.round_room_angle_to_resulution()

        if draw:
            self.draw_arm_angles()
        return self.room_angles

    def find_arm_angles(self)->list|None:
        if self.hand_3d is None or self.shoulder_3d is None:
            self.arm_angles = [None, None]
        else:
            arm_azimuth = find_azimuth_angle(self.hand_3d, self.shoulder_3d)
            arm_elevation = find_elevation_angle(self.hand_3d, self.shoulder_3d)

            self.arm_angles = self.angle_smoother.add_and_get([arm_azimuth, arm_elevation])
        return self.arm_angles

    def find_3d_hand_shoulder_with_depth_frame(self, depth_frame:object)->tuple[list|None]:
        args = (depth_frame, 
                self.mirrowed_frame, 
                self.cam_angle, 
                self.cam_intrinsics)
        self.hand_3d =      rs_pixel_to_3d(self.hand_pixel_xy, *args)
        self.shoulder_3d =  rs_pixel_to_3d(self.shoulder_pixel_xy, *args)
        return self.hand_3d, self.shoulder_3d

    def find_3d_hand_shoulder_with_depth(self, hand_depth:float, shoulder_depth:float)->tuple[list|None]:
        args = (self.mirrowed_frame, 
                self.cam_angle, 
                self.cam_intrinsics)
        self.hand_3d =      rs_pixel_to_3d(self.hand_pixel_xy, hand_depth, *args)
        self.shoulder_3d =  rs_pixel_to_3d(self.shoulder_pixel_xy, shoulder_depth, *args)
        return self.hand_3d, self.shoulder_3d
        
    def aprox_room_azimuth(self):
        angle = self.arm_angles[0]
        if angle is not None:
            sliding_factor = (90-abs(angle))/90
            correction = sliding_factor * self.room_azemuth_aprox_corection_max

            if self.mirrowed_frame:
                correction *= -1

            if self.hand_side == 'left':
                new_angle = angle - correction
            elif self.hand_side == 'right':
                new_angle = angle + correction

            self.room_angles[0] = new_angle

    def map_room_angles_to_45_deg_steps(self):
        for i, angle in enumerate(self.room_angles):
            if angle is None:
                continue
            self.room_angles[i] = map_threshold(angle,
                                                (-70,-25,25,70),
                                                (-90,-45,0,45,90)
                                                )

    def round_room_angle_to_resulution(self):
        res = self.angle_resulution
        for i, angle in enumerate(self.room_angles):
            if angle is None:
                continue
            self.room_angles[i] = -round(angle/res)*res

    def pointion_into_camera_check(self,use_pixel_coordinats=False):
        """ if shoulder and hand are overlapping in the frame, persine is pointing to the camera """
        if use_pixel_coordinats:
            return close_to(self.intersection_distance_pixel, self.hand_pixel_xy, self.shoulder_pixel_xy)
        else:
            return close_to(self.intersection_distance, self.hand_3d, self.shoulder_3d)

    def draw_arm_angles(self):
        if self.draw_frame is None:
            raise "no frame to draw on"
        if self.hand_pixel_xy is None:
            raise "no hand pixel position to draw"
        if self.shoulder_pixel_xy is None:
            raise "no shoulder pixel position to draw"
        p1_2d = self.hand_pixel_xy
        p2_2d = self.shoulder_pixel_xy
        p3_2d = p2_2d.copy()
        p3_2d[1] += 100 # draw in y direction
        text = ''
        azimuth, elevation = self.arm_angles
        if self.arm_angles[0] is not None:
            text += str(round(azimuth)) 
        if elevation is not None:
            text += '/' 
            text += str(round(elevation)) 
        if not text:
            text = 'None'
        draw_angle_between_points(self.draw_frame,text,p1_2d,p2_2d,p3_2d,(-10,-10), S.green)

    @property
    def azimuth(self)->float:
        return self.room_angles[0]

    @property
    def elevation(self)->float:
        return self.room_angles[1]

    @property
    def angles(self)->list:
        return [*self.room_angles, *self.arm_angles]

    @property
    def hand(self)->list:
        if self.hand_3d:
            return self.hand_3d.copy()
        return None

    @property
    def shoulder(self)->list:
        if self.shoulder_3d:
            return self.shoulder_3d.copy()
        return None
