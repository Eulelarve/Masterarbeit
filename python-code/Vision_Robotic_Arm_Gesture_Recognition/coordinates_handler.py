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


def mediapipe_pose_world_to_3d(pose_world_landmarks, cam_angle):

    pts = np.asarray(pose_world_landmarks, dtype=np.float64)
    if pts.ndim == 1:
        pts = pts.reshape(1, -1)

    if len(pts[0]) > 3: 
        pts = pts[:, 1:4]
    
    # change coordinates: +x = rechts, +y  = unten , +z = vorne (weg von der kamera)
    # for i,(xa,ya,za) in enumerate(pts):
    #     xn = xa
    #     yn = ya
    #     zn = za 
    #     pts[i] = [xn,yn,zn]    

    theta = np.deg2rad(cam_angle)

    x = pts[:, 0]
    y = pts[:, 1]
    z = pts[:, 2]

    y0 = y*np.cos(theta) + z*np.sin(theta)
    z0 = -y*np.sin(theta) + z*np.cos(theta)

    y0 += 2 # so y = 0 is ruffly at the camera position if person stants in the room center
    z0 += 1 # so z = 0 ruffly on the flore hight

    i = range(len(x))
    pts = np.column_stack((i, x, y0, z0))
    return pts

def rs_pixel_to_3d(depth_frame, intrinsics, px:int, py:int, mirrowed_frame=False):
    """
    px, py: Pixelkoordinaten im Colorbild
    Rückgabe: np.array([X,Y,Z]) in Metern
    """
    h = depth_frame.get_height()
    w = depth_frame.get_width()
    x = int(px)
    y = int(py)
    if mirrowed_frame:
        x = w - x

    # Out-of-range prüfen
    if x < 0 or x >= w or y < 0 or y >= h:
        return None
    depth = depth_frame.get_distance(x, y)

    if depth <= 0:
        return None
    point = rs.rs2_deproject_pixel_to_point(
        intrinsics,
        [x, y],
        depth
    )
    if mirrowed_frame:
        point[0] = w - point[0]
        
    return np.array(point)


def rs_pixel_list_to_3d(depth_frame, intrinsics,pixel_coords_list:tuple, cam_angle:float, mirrowed_frame = False):
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

    theta = np.deg2rad(cam_angle)

    pts_3d = []
    for i ,(x,y) in enumerate(pts):
        p3d = rs_pixel_to_3d(depth_frame, intrinsics, x, y,mirrowed_frame)
        if p3d is None:
            pts_3d.append(None)
            continue
        x,y,z = p3d
        # angle compensation
        y = z*np.sin(theta) + y*np.cos(theta)
        z = z*np.cos(theta) + -y*np.sin(theta)
        pts_3d.append([i,x,y,z])

    return pts_3d
