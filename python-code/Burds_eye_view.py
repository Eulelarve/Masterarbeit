

import numpy as np
import cv2
import time

from Vision_Robotic_Arm_Gesture_Recognition.analyse import find_files
import Vision_Robotic_Arm_Gesture_Recognition.settings as S
# import pyrealsense2 as rs

# pipeline = rs.pipeline()
# config = rs.config()

# config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

# profile = pipeline.start(config)

# intr = (
#     profile
#     .get_stream(rs.stream.color)
#     .as_video_stream_profile()
#     .get_intrinsics()
# )

# K = np.array([
#     [intr.fx, 0,       intr.ppx],
#     [0,       intr.fy, intr.ppy],
#     [0,       0,       1]
# ])

# print(K)
# print(intr.coeffs)

# pipeline.stop()

# # findet kamera position
# success, rvec, tvec = cv2.solvePnP(
#     object_points,
#     image_points,
#     K,
#     dist_coeffs,
#     flags=cv2.SOLVEPNP_ITERATIVE
# )

# Für eine D455 wurden beispielsweise bei 1280×720 RGB folgende Werte ausgegeben:

fx  = 642.29
fy  = 641.56
ppx = 652.59
ppy = 360.33

# kameramatrix
K = np.array([
    [fx, 0,  ppx],
    [0,  fy, ppy],
    [0,  0,    1]
])

pitch = np.deg2rad(32.5)

# winkel- und rotationsvektor der kamera
rvec = np.array([
    pitch,
    0,
    0
], dtype=np.float64)

# Translationsvektor der Kamera
cam_hight = 2.70 # höhe der kamera in meter
tvec = np.array([
    [0],
    [0],
    [cam_hight]
], dtype=np.float64)

R, _ = cv2.Rodrigues(rvec)
t = tvec.flatten()
print(t)
print(R)
H = K @ np.column_stack((R[:,0], R[:,1], t))

# bx = 5
# by = 5
# world = np.array([
#     [-bx, -by, 0],
#     [ bx, -by, 0],
#     [-bx, by, 0],
#     [ bx, by, 0]
# ], dtype=np.float64)

# image_points, _ = cv2.projectPoints(
#     world,
#     rvec,
#     tvec,
#     K,
#     None
# )

# image_points = image_points.reshape(-1,2).astype(np.float32)
# dx = 700
# dy = 1000
# dst = np.array([
#     [0,0],
#     [dx,0],
#     [0,dy],
#     [dx,dy]
# ], dtype=np.float32)

# H = cv2.getPerspectiveTransform(
#     image_points,
#     dst
# )

videos = find_files(S.video_folder, ending=('.mp4', '.avi', '.mov'),names_only=True)
print('videos: ',len(videos))
# v1-11
v1 = videos[0]
v2 = videos[1]
v3 = videos[2]
v4 = videos[3]
v5 = videos[4]
v6 = videos[5]
v7 = videos[6]
v8 = videos[7]
v9 = videos[8]
v10 = videos[9]
v11 = videos[10]
sourse = S.video_folder + v9

#---------------------------

# Originalbild laden
# img = cv2.imread('road.jpg')
# h, w = img.shape[:2]
def calc_h(src_pts=[],dst_pts=[],h=720):
    # 4 Punkte im Originalbild (Quadrat/Raute auf der Straße)
    if  len(src_pts) != 4:
        src_pts = np.float32([[50, 200], [200, 150], [400, 150], [550, 200]])

    # 4 Zielpunkte für die Bird's-Eye-View (Rechteck)
    dst_pts = np.float32([[src_pts[0][0],h], [src_pts[0][0],0], [src_pts[3][0],0], [src_pts[3][0],h]])
    print(src_pts)# test
    print(dst_pts)# test

    # Homographie-Matrix berechnen
    H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC)
    return H
# Transformation anwenden
# warped_img = cv2.warpPerspective(img, H, (w, h))   

#----------------------------
# clicked_points = []
# COLOR = (0, 0, 255)
# POINTS = 4

# def mouse_callback(event, x, y, flags, param):
#     if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < POINTS:
#         clicked_points.append([x, y])
#         print(f"Punkt {len(clicked_points)}: ({x}, {y})")

#         img = param.copy()
#         for p in clicked_points:
#             cv2.circle(img, tuple(p), 5, COLOR, -1)
#         cv2.imshow("Waehle 4 Punkte", img)


clicked_points = []
mouse_pos = None
base_img = None

def mouse_callback(event, x, y, flags, param):
    global mouse_pos

    if event == cv2.EVENT_MOUSEMOVE:
        mouse_pos = (x, y)

    elif event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
        clicked_points.append((x, y))
        mouse_pos = (x, y)
#-------------------------



video_capture = cv2.VideoCapture(sourse)
max_fps = video_capture.get(cv2.CAP_PROP_FPS)
frame_time = 1 / max_fps
last_frame_time = time.perf_counter()

if not video_capture.isOpened():
    raise RuntimeError("no video found")

#------------------------
success, frame = video_capture.read()
if not success:
    raise RuntimeError("Kein Frame gelesen")

cv2.imshow("Waehle 4 Punkte", frame)
cv2.setMouseCallback("Waehle 4 Punkte", mouse_callback, frame)
print("Bitte 4 quellen Punkte anklicken, starte unten links dan im urzeigersin!")

#-----------------
while len(clicked_points) < 4:

    img = frame.copy()

    # bereits gewählte Punkte
    for p in clicked_points:
        cv2.circle(img, p, 5, (0, 0, 255), -1)

    # Linien zwischen den bereits gewählten Punkten
    for i in range(1, len(clicked_points)):
        cv2.line(img, clicked_points[i-1], clicked_points[i], (0, 255, 0), 2)

    # Dynamische Linie vom letzten Klick zur Maus
    if mouse_pos is not None and len(clicked_points) > 0:
        cv2.line(img, clicked_points[-1], mouse_pos, (255, 0, 0), 2)

    cv2.imshow("Waehle 4 Punkte", img)
    cv2.waitKey(10)
#-----------------

src_pts = np.float32(clicked_points)

cv2.destroyWindow("Waehle 4 Punkte")

H = calc_h(src_pts=src_pts)
#-----------------------


pause = False
while True:
    if time.perf_counter()-last_frame_time<frame_time:
        continue
    last_frame_time = time.perf_counter()

    if not pause:
        success, frame = video_capture.read()

    if not success or frame is None:
        break
    
    h, w = frame.shape[:2]

    bird = cv2.warpPerspective(
        frame,
        H,
        (w,h)
    )

    cv2.imshow(
    'Birds Eye View',
    frame
    )

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if key == ord(' '):
        pause = not pause

video_capture.release()
cv2.destroyAllWindows()