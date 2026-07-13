print('test file')
import numpy as np
import mediapipe as mp
import cv2
def mediapipe_pose_world_to_global(pose_world_landmarks, rvec_cam, tvec_cam):
    """
    Transform MediaPipe pose_world_landmarks into a global/world coordinate system.

    Parameters
    ----------
    pose_world_landmarks : array-like, shape (N, 3) or (N, 4)
        MediaPipe 3D pose landmarks in meters. Only x, y, z are used.
        The coordinates are assumed to be expressed in the MediaPipe pose world frame
        (origin near the center between the hips).
    rvec_cam : array-like, shape (3,)
        Camera rotation vector (Rodrigues) that describes the camera orientation
        in the global/world coordinate system.
    tvec_cam : array-like, shape (3,)
        Camera translation vector that describes the camera position in the
        global/world coordinate system.

    Returns
    -------
    np.ndarray
        Landmarks transformed into the global/world coordinate system, shape (N, 3).
    """
    pts = np.asarray(pose_world_landmarks, dtype=np.float64)

    if pts.ndim == 1:
        pts = pts.reshape(1, -1)

    if len(pts[0]) > 3: 
        pts = pts[:, 1:4]

    rvec_cam = np.asarray(rvec_cam, dtype=np.float64).reshape(3, 1)
    tvec_cam = np.asarray(tvec_cam, dtype=np.float64).reshape(3, 1)

    R_cam, _ = cv2.Rodrigues(rvec_cam)

    pts_global = (R_cam @ pts.T + tvec_cam).T
    return pts_global


# main

mp_pose = mp.solutions.pose

# Beispielwerte für deine Kamera:
rvec_cam = np.array([np.deg2rad(30), 0.0, 0.0], dtype=np.float64)
tvec_cam = np.array([0.0, 0.0, 1.7], dtype=np.float64)

# Beispiel MediaPipe-Punkt
pose_world_landmarks = np.array([
    [0.10, .50, -0.30],
    [0.15, .10, -0.25],
])

global_pts = mediapipe_pose_world_to_global(
    pose_world_landmarks,
    rvec_cam,
    tvec_cam
)

print(global_pts)



i = [[1,2,3],[4,5,6],[7,8,9]]
for e,ii in enumerate(i):
    i[e] = [-ii[0],ii[2],ii[1]]    

print(i)