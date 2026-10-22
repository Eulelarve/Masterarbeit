""" Stitchi 1.0

Coordinate conversion and camera/room geometry helpers.

Converts image pixels and RealSense depth into 3D points, retrieves depth at
landmark pixels, estimates or converts MediaPipe world landmarks, and applies
camera-position, mirroring, and inclination compensation. Used by
MediaPipe_handler.py and angle_handler.py to obtain coordinates suitable for
room-relative pointing calculations.
"""

import math
import numpy as np
import pyrealsense2 as rs
import settings as S

            
def offset_landmarks(landmarks, dx=0, dy=0, dz=0):
    """
    Verschiebt MediaPipe-Landmarks.
    will change the inputed objece!

    input can be:
        results.pose_landmarks.landmark
        results.multi_hand_landmarks[i].landmark
    not just:
        results.pose_landmarks
        results.multi_hand_landmarks[i]


    """
    for lm in landmarks:

        if dx:
            lm.x += dx
        if dy:
            lm.y += dy
        if dz:
            lm.z += dz

def get_center_of_landmarks(pose_landmarks, landmark_indices, round_to_int=True):
    """ calculate the center of the given landmarks
    Args:
        pose_landmarks: list of pose landmarks
        landmark_indices: list of indices of the landmarks to calculate the center from
        round_to_int: whether to round the center coordinates to integers
    Returns:
        center: the center as a tuple (x, y) or (x,y,z)
    """
    x_sum = sum([pose_landmarks[i][1] for i in landmark_indices])
    y_sum = sum([pose_landmarks[i][2] for i in landmark_indices])
    center_x = x_sum / len(landmark_indices)
    center_y = y_sum / len(landmark_indices)

    if round_to_int:
        center_x = round(center_x)
        center_y = round(center_y)

    try:
        z_sum = sum([pose_landmarks[i][3] for i in landmark_indices])
        center_z = z_sum / len(landmark_indices)
        if round_to_int:
            center_z = round(center_z)

        return [center_x, center_y, center_z]
    except:
        return [center_x, center_y]

def add_estimated_cam_to_human_dist(point_3d:tuple)->list:
    x = point_3d[0]
    y = point_3d[1]
    z = point_3d[2] + math.dist(S.room_center, S.cam_pos_in_room) # so z = 0 is ruffly at the camera position if person stants in the room center
    return [x,y,z]

def add_estimated_hip_hight(point_3d:tuple)->list:
    x = point_3d[0]
    y = point_3d[1] + S.estimated_hip_hight # the hip pos is the origin (0,0,0) position in mediapipe world coordinats
    z = point_3d[2] 
    return [x,y,z]

def mediapipe_world_to_room(world_landmarks):
    pts = []
    for (i,x,y,z) in world_landmarks:
        xyz = x,y,z
        xyz = compensate_cam_inclination_angle(xyz)
        xyz = add_estimated_cam_to_human_dist(xyz)
        xyz = add_estimated_hip_hight(xyz)
        ixyz = [i,*xyz]
        pts.append(ixyz)
    return pts

def mediapipe_pose_to_3d(pose_landmarks:tuple[int], pose_wold_landmarks, intrinsics)->list:
    pts = []
    for (i,x,y) in pose_landmarks:
        depth = pose_wold_landmarks[i][3]
        xyz = rs.rs2_deproject_pixel_to_point(
            intrinsics,
            [x, y],
            depth
        )
        xyz = compensate_cam_inclination_angle(xyz)
        xyz = add_estimated_cam_to_human_dist(xyz)
        ixyz = (i,*xyz)
        pts.append(ixyz)

    return pts

def rs_get_depth(depth_frame, pixel_xy:tuple, mirrowed_x_pixel:bool)->float|None:
    h = depth_frame.get_height()
    w = depth_frame.get_width()
    x = int(pixel_xy[0])
    y = int(pixel_xy[1])
    # Out-of-range prüfen
    if x < 0 or x >= w or y < 0 or y >= h:
        return None

    if mirrowed_x_pixel:
        x = w - x

    return depth_frame.get_distance(x, y)

def rs_pixel_to_meter(intrinsics:object, pixel_xy:tuple, depth:float)->list:
    if intrinsics is None:
        raise "no cam intrinsics are given"
    return rs.rs2_deproject_pixel_to_point(intrinsics, pixel_xy, depth)

def rs_pixel_to_3d(pixel_xy:tuple, depth_frame_or_depth:object|float|int, mirrowed_x_pixel:bool, cam_intrinsics:object|None=None)->list|None:
    """
    cam intrinsics are not needed if a depth frame is given
    pixel_xy: Pixelkoordinaten im Colorbild
    return:  list [X,Y,Z] in Metern
    """
    if type(depth_frame_or_depth) in [int, float]:
        depth = depth_frame_or_depth
    else: # is depth frame
        depth = rs_get_depth(depth_frame_or_depth, pixel_xy, mirrowed_x_pixel)
        if cam_intrinsics is None:
            cam_intrinsics = depth_frame_or_depth.profile.as_video_stream_profile().intrinsics

    if depth is None:
        return None
    
    x,y,z = rs_pixel_to_meter(cam_intrinsics, pixel_xy, depth)

    if mirrowed_x_pixel:
        x = - x

    x,y,z = compensate_cam_pos((x,y,z))
    x,y,z = compensate_cam_inclination_angle((x,y,z))
        
    return [x,y,z]

def compensate_cam_pos(point_3d):
    x = point_3d[0] + S.cam_pos_in_room[0]
    y = point_3d[1] + S.cam_pos_in_room[1]
    z = point_3d[2] + S.cam_pos_in_room[2]
    return [x,y,z]


def rs_pixel_list_to_3d(depth_frame, pixel_coords_list:tuple, cam_angle:float, mirrowed_frame = False):
    """ 
        returns a np.array with i,x,y,z
         i: index
        +x: right
        +y: down
        +z: away vom the cam
    """

    pts = np.asarray(pixel_coords_list, dtype=np.float64)
    if pts.ndim == 1:
        pts = pts.reshape(1, -1)

    if len(pts[0]) > 2: 
        pts = pts[:, 1:3]


    pts_3d = []
    for pt in pts:

        p3d = rs_pixel_to_3d(pixel_xy=pt, depth_frame_or_depth=depth_frame, mirrowed_x_pixel=mirrowed_frame, cam_angle=cam_angle, cam_intrinsics=None)
        pts_3d.append(p3d)

    return pts_3d

def compensate_cam_inclination_angle(point_3d:tuple)->list:
    theta = np.deg2rad(S.cam_inclination_angle)
    x,y,z = point_3d
    y = z*np.sin(theta) + y*np.cos(theta)
    z = z*np.cos(theta) + -y*np.sin(theta)
    return [x,y,z]