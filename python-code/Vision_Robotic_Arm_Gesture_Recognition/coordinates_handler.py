from datetime import datetime
import cv2
import math
import numpy as np
import pyrealsense2 as rs
try:
    import settings as S
except:
    import Vision_Robotic_Arm_Gesture_Recognition.settings as S

            

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
    # landmarks_copy = deepcopy(pose_or_hand_landmarks)

    # # Überprüfen, ob es das übergeordnete Landmark-Objekt ist oder bereits die Liste der Landmark-Objekte
    # if hasattr(pose_or_hand_landmarks, 'landmark'):
    #     landmarks = pose_or_hand_landmarks.landmark
    # else:
    #     landmarks = pose_or_hand_landmarks
    
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

def add_estimated_cam_distance(landmarks_3d:tuple)->list:
    pts = []
    for (i,x,y,z) in landmarks_3d:
        z0 = z + S.dist_cam_to_room_center # so z = 0 is ruffly at the camera position if person stants in the room center
        ixyz = [i,x,y,z0]
        pts.append(ixyz)
    return pts

def mediapipe_pose_to_3d(pose_landmarks:tuple[int], pose_wold_landmarks, intrinsics, cam_angle:float)->list:
    pts = []
    for (i,x,y) in pose_landmarks:
        depth = pose_wold_landmarks[i][3]
        xyz = rs.rs2_deproject_pixel_to_point(
            intrinsics,
            [x, y],
            depth
        )
        ixyz = (i,*xyz)
        pts.append(ixyz)
    pts = compensate_cam_angle(pts, cam_angle)
    pts = add_estimated_cam_distance(pts)
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

def rs_pixel_to_3d(pixel_xy:tuple, depth_frame_or_depth:object|float|int, mirrowed_x_pixel:bool, cam_angle:float|None, cam_intrinsics:object|None=None)->list:
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

    x,y,z = rs_pixel_to_meter(cam_intrinsics, pixel_xy, depth)

    if mirrowed_x_pixel:
        x = - x

    if cam_angle:
        x,y,z = compensate_cam_angle((x,y,z), cam_angle)
        
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

def compensate_cam_angle(point_3d:tuple, cam_elevation:float)->list:
    theta = np.deg2rad(cam_elevation)
    x,y,z = point_3d
    y = z*np.sin(theta) + y*np.cos(theta)
    z = z*np.cos(theta) + -y*np.sin(theta)
    return [x,y,z]